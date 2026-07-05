# Goal
I want to refactor the navigation panels
- drop the timeline panel
- instead, show the year right aligned on each item of the tree
- in era_year, dropped the content in parenthesis, e.g. "（戊寅，公元前四零三年）"
- in higher level nodes, show the year range

## Things to consider
- we may need to regenerate contents in 'semantic_json' from 'raw_json_converted'
- previously the year field was added late using 'scripts/add_year_field.py'. now this maybe integrated into the new script.（戊寅，公元前四零三年）