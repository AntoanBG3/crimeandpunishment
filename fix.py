import os

files = [r'game_engine\item_interaction_handler.py', r'game_engine\npc_interaction_handler.py']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Fix the bug
    content = content.replace('self.get_current_time_period()', 'self.world_manager.get_current_time_period()')
    
    # Add pylint disables at the top
    if '# pylint: disable=no-member, attribute-defined-outside-init' not in content:
        content = '# pylint: disable=no-member, attribute-defined-outside-init\n' + content
        
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Done!')
