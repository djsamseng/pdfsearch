# Algorithm

## Database
#### Elements
| id | bbox     | page | data | elem_type |
| -- | -------- | ---- | ---- | --------- |
| 01 | [100,100,200,200] | 9    | { "label": "A21" } | elem |
| 02 | [row of window schedule] | 3 | {"type": "A", "MNFCT": "B"} | schedule_row |
| 03 | [cell of window schedule] | 3 | {"MNFCT": "B"} | schedule_cell |
| 04 | [cell of window schedule] | 3 | {"MNFCT": "B"} | schedule_cell |

#### Links
| from_id | to_id | link_type |
| ------- | ----- | --------- |
| 01      | 02    | instance_of |
| 03      | 02    | cell_of_row |

### Answering Questions
- How many windows are made by MNFCT B?
  - schedule_rows = SELECT to_id WHERE data["MNFCT"] == "B" AND link_type == "cell_of_row"
  - SELECT from_id WHERE to_id in schedule_rows AND link_type = "instance_of"
- How much square feet have finish C1?
  - C1 is a value of ceiling `{"ceiling": "C1"}`
  - link_type `cell_of_row` has to_id `schedule_row`
  - `schedule_row` has `{"name_of_room": "Dining Room"}`
  - `square_feet` also has `{"name_of_room": Dining Room"}`
- What can I search for?
  - SELECT data WHERE elements.id = links.from_id AND links.link_type = "cell_of_row"


## PDF Processing
