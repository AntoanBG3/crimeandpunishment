"""Reproducible offline gameplay scenarios, always run in a disposable child process."""

import argparse
from collections import deque
import contextlib
import io
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class QuietTerminal:
    """Minimal injected terminal for engine scenarios; retains no narrative text."""

    narrative_pace_enabled = False

    def __init__(self):
        self.emitted = 0

    def write_line(self, *args, **kwargs):
        self.emitted += 1

    write_renderable = write_line
    write_narrative = write_line
    write_dialogue = write_line
    ensure_blank_line = write_line
    clear_screen = write_line

    def read_line(self, *args, **kwargs):
        return 'Farewell'

    def set_completer_provider(self, provider):
        self.completer = provider

    def set_toolbar_provider(self, provider):
        self.toolbar = provider

    def set_narrative_pace(self, enabled):
        self.narrative_pace_enabled = enabled

    def get_narrative_pace(self):
        return self.narrative_pace_enabled

    def toolbar_active(self):
        return False

    def separator(self):
        return '---'

    def status(self, message):
        return contextlib.nullcontext()


class DiscardText(io.TextIOBase):
    def write(self, text):
        return len(text)


def build_game(name, seed, stationary=False):
    from game_engine.game_state import Game

    game = Game(rng=random.Random(seed), terminal_io=QuietTerminal())
    game.world_manager.load_all_characters()
    game.player_character = game.all_character_objects[name]
    game.player_character.is_player = True
    game.current_location_name = game.player_character.current_location
    game.low_ai_data_mode = True
    if stationary:
        # An explicit fixture: retain authored starting locations but disable schedules.
        # Dynamic NPC scheduling is exercised separately in the engine soak.
        for character in game.all_character_objects.values():
            character.schedule = {}
    game.world_manager.update_npcs_in_current_location()
    return game


def execute(game, text):
    command, argument = game.command_handler.parse_action(text)
    if command is None:
        return
    result = game.command_handler._process_command(command, argument)
    if not result.special_flag:
        game.world_manager._update_world_state_after_action(
            command, result.action_taken, result.time_to_advance
        )
    assert game.player_character is not None, text
    assert game.player_character.current_location == game.current_location_name, text
    for character in game.all_character_objects.values():
        assert all(item.get('quantity', 1) > 0 for item in character.inventory), text


def travel(game, destination):
    from game_engine.location_module import LOCATIONS_DATA

    pending = deque([(game.current_location_name, [])])
    visited = set()
    while pending:
        location, path = pending.popleft()
        if location == destination:
            for target in path:
                execute(game, 'move to ' + target)
            assert game.current_location_name == destination
            return
        if location in visited:
            continue
        visited.add(location)
        for target in LOCATIONS_DATA[location].get('exits', {}):
            pending.append((target, path + [target]))
    raise AssertionError(f'No route to {destination}')


def endings(seed):
    from game_engine.objective_progression import MAIN_OBJECTIVE_BY_CHARACTER

    reached = {}
    for name in ('Rodion Raskolnikov', 'Sonya Marmeladova', 'Porfiry Petrovich'):
        game = build_game(name, seed, stationary=True)
        target = 'Sonya Marmeladova' if name == 'Rodion Raskolnikov' else 'Rodion Raskolnikov'
        travel(game, game.all_character_objects[target].current_location)
        execute(game, 'talk to ' + target)
        if name == 'Porfiry Petrovich':
            execute(game, 'persuade Rodion that confession will help')
            execute(game, 'persuade Rodion that confession will help')
        else:
            execute(game, 'talk to ' + target)
        if name == 'Sonya Marmeladova':
            execute(game, "give sonya's cypress cross to Rodion")
        execute(game, 'confess')
        if name == 'Rodion Raskolnikov':
            travel(game, 'Police Station (General Area)')
            execute(game, 'confess')
        assert game.world_manager._check_game_ending_conditions(), name
        stage = game.player_character.get_current_stage_for_objective(MAIN_OBJECTIVE_BY_CHARACTER[name])
        reached[name] = stage['stage_id']
        game.gemini_api.close()
    return {'endings': reached, 'npc_fixture': 'authored locations, stationary schedules'}


def engine(seed, actions):
    from game_engine.location_module import LOCATIONS_DATA

    rng = random.Random(seed)
    game = build_game('Rodion Raskolnikov', seed)
    durations = []
    samples = []
    tracemalloc.start()
    start = time.perf_counter()
    for index in range(actions):
        commands = ['look', 'wait', 'think', 'inventory', 'status', 'objectives', 'journal', 'actions']
        commands += ['move to ' + name for name in LOCATIONS_DATA[game.current_location_name]['exits']]
        command = rng.choice(commands)
        tick = time.perf_counter()
        execute(game, command)
        durations.append(time.perf_counter() - tick)
        if index % 500 == 0:
            game.save_game('audit')
            assert game.load_game('audit')
        if (index + 1) % max(1, actions // 5) == 0:
            samples.append({'actions': index + 1, 'retained_bytes': tracemalloc.get_traced_memory()[0],
                            'events': len(game.key_events_occurred)})
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    game.gemini_api.close()
    return {'actions': actions, 'seconds': time.perf_counter() - start,
            'p95_command_ms': sorted(durations)[int(len(durations) * .95) - 1] * 1000,
            'median_command_ms': statistics.median(durations) * 1000,
            'retained_bytes': current, 'peak_bytes': peak, 'samples': samples,
            'event_count': len(game.key_events_occurred), 'day': game.current_day}


async def tui(seed, actions):
    from game_engine import terminal
    from game_engine.tui_app import CrimeAndPunishmentApp, CommandInput
    from textual.widgets import Input

    count = 0

    def runner():
        nonlocal count
        for _ in range(actions):
            line = terminal.read_line('> ')
            assert line == 'look'
            terminal.write_line('A cold wind crosses the square.')
            count += 1
        terminal.read_line('> ')

    app = CrimeAndPunishmentApp(game_runner=runner)
    tracemalloc.start()
    start = time.perf_counter()
    async with app.run_test(size=(40, 12)) as pilot:
        for _ in range(actions):
            # Wait for worker output/input handoff, not an arbitrary sleep per command.
            while count < _ or not getattr(app, '_accepting_input', True):
                await pilot.pause(0.001)
            widget = app.query_one(CommandInput)
            app.on_input_submitted(Input.Submitted(widget, 'look'))
        while count < actions:
            await pilot.pause(0.001)
        await pilot.pause(0.01)
        retained_history = len(app.query_one(CommandInput).history)
        retained_lines = len(app.query_one('RichLog').lines)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert not app._game_thread.is_alive()
    return {'commands': count, 'seconds': time.perf_counter() - start,
            'retained_history': retained_history, 'retained_log_lines': retained_lines,
            'retained_bytes': current, 'peak_bytes': peak}


def console(binary=None):
    command = [str(binary)] if binary else [sys.executable, str(ROOT / 'main.py')]
    # Frozen Python can use the Windows locale even when the launcher uses UTF-8.
    # Smoke markers are ASCII; inspect bytes without decoding unrelated prose.
    result = subprocess.run(command + ['--no-tui'], input=b'\n1\nlook\nquit\nn\n',
                            capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, f'exit={result.returncode}; stderr={result.stderr}'
    for marker in ('Choose Your Character', "Raskolnikov's Garret", 'Exiting game. Goodbye.'):
        assert marker.encode('ascii') in result.stdout, marker
    eof = subprocess.run(command + ['--no-tui'], input=b'', capture_output=True,
                         timeout=30, check=False)
    assert eof.returncode == 0, eof.stderr
    version = subprocess.run(command + ['--version'], capture_output=True,
                             timeout=30, check=True)
    assert b'Crime and Punishment ' in version.stdout
    return {'exit_code': result.returncode, 'eof_exit_code': eof.returncode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('engine', 'endings', 'tui', 'console'), required=True)
    parser.add_argument('--seed', type=int, default=1729)
    parser.add_argument('--actions', type=int, default=10000)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    if args.actions < 1:
        parser.error('--actions must be positive')
    if not args.child:
        child_arguments = [*sys.argv[1:], '--child']
        if args.binary:
            child_arguments += ['--binary', str(args.binary.resolve())]
        with tempfile.TemporaryDirectory(prefix='crime audit ü ') as directory:
            env = {key: value for key, value in os.environ.items()
                   if key not in ('GEMINI_API_KEY', 'GOOGLE_API_KEY')}
            env.update(HOME=directory, USERPROFILE=directory, NO_COLOR='1', PYTHONUTF8='1')
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()), *child_arguments],
                                    cwd=directory, env=env, text=True, encoding='utf-8',
                                    capture_output=True, timeout=args.timeout, check=False)
            if result.returncode:
                sys.stderr.write(result.stderr)
                raise SystemExit(result.returncode)
            print(result.stdout.strip())
        return
    with contextlib.redirect_stdout(DiscardText()):
        if args.scenario == 'tui':
            import asyncio
            outcome = asyncio.run(tui(args.seed, args.actions))
        elif args.scenario == 'console':
            outcome = console(args.binary)
        elif args.scenario == 'endings':
            outcome = endings(args.seed)
        else:
            outcome = engine(args.seed, args.actions)
    print(json.dumps({'scenario': args.scenario, 'seed': args.seed, **outcome}))


if __name__ == '__main__':
    main()
