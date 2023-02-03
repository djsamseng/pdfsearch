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
### Hard Coded Algorithm
1. Look for = [windowSchedule, doorSchedule, lightingSchedule, finishSchedule, houseName, architectName, windows, doors, lights]
2. When find doorSchedule, update search rule doors
   1. For each row create rowId, cellId and append a search rule
   ```python3
   import uuid
   uuid.uuid4()
   ```
   2. When that search rule is triggered, create elem, create link
3. Each page predicts what schedule should be used on it
   1. Hard code for now
4. Get all data and merge client side
   1. `SELECT * FROM elems WHERE pdf_id="pdfId" AND page_number=4`
   2. `SELECT * FROM links WHERE from_id = ANY(ARRAY[1,2,3])`
   3. `SELECT * FROM links WHERE to_id = ANY(ARRAY[1,2,3])`
5. On hover over bbox
   1. If elem_type == "element", get schedule row elem, get all instance_of that row, display row elem, highlight all instances
   2. If elem_type == "schedule_row", get all instance_of of that row, highlight all instances
6. On Search, send an API request to AI

### AI Algorithm
