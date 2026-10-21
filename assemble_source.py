from pathlib import Path
import json
p=Path(__file__).parent
data=json.loads((p/'measured_profiles.json').read_text())
template=(p/'model_template.py').read_text()
source=template.replace('# PROFILE_DATA','import json\nPROFILES = json.loads('+repr(json.dumps(data))+')')
(p/'model_mcp.py').write_text(source,encoding='utf-8')
human=template.replace('# PROFILE_DATA',"from pathlib import Path\nimport json\nPROFILES = json.loads((Path(__file__).parent/'measured_profiles.json').read_text())")
(p/'model.py').write_text(human,encoding='utf-8')
print('model.py bytes',len(human),'MCP source bytes',len(source))
