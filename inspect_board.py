import json
from pathlib import Path

board = json.loads(Path('output/board/project_board_current.json').read_text(encoding='utf-8'))
print('TOP KEYS:', list(board.keys()))
print('status:', board.get('status'))
stages = board.get('stages', [])
print('stages count:', len(stages))
for s in stages[:3]:
    print('\n--- stage keys:', list(s.keys()))
    print('  stage_id/id:', s.get('stage_id') or s.get('id') or s.get('name') or '?')
    print('  status:', s.get('status'))
    out = s.get('output') or s.get('result') or s.get('outputs')
    print('  output type:', type(out), '| keys:', list(out.keys()) if isinstance(out, dict) else out)
    print('  summary:', str(s.get('summary', ''))[:200])
