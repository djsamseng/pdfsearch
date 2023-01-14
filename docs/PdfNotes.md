# Notes About Architect PDFs

## Algorithm
- Instead of creating a summary page we want just want to make a pdf viewer
- Look for symbols on all pages and say hey we found 10 of these symbols on the "ATTIC FLOOR ELECTRICAL PLAN E-4"

### Michael Smith Flow
1. Get Architect from location on first page (top right)
2. Get Residence from location on first page (top center)
3. Look for keywords "DOOR SCHEDULE", "WINDOW SCHEDULE", "LIGHTING LEGEND". Parse these tables for symbols.
4. Index the symbols that we want to find into a KDTree based on size, shape, number of lines etc.
5. Find these symbols on each page, put the counts found on each page with page name
6. Regions gather votes of what they are
7. This gives context to the symbol (I'm a light on the second floor electrical plan)

### Advanced
- Divide and conquer, vote on classifying regions and convince each other. But how do they know how to vote?
- What is a lighting legend
  - A box with variable height and width
  - Lighting Legend on top
  - 3 columns Type, Symbol, Description
- What is a construction plan
  - Lots of long lines
  - Symbols and labels
  - Classify things to belong to be grouped
    - I might be close to something I'm not grouped with
    - However my group may overall vote that it's not grouped with what I may think I'm grouped with
    - Additionally what I'm close to may be a part of a group that votes that it's not grouped with my group
- What structure is shared by all/most pages


## Architects
### Michael Smith
- Drawing index on the first page is out of date
  - Does not match order of pages
  - "E-1 BASEMENT ELECTRICAL PLAN (TBD)" (drawing index) != "E-1 BASEMENT ELECTRICAL PLAN" (actual)
  - "TITLE SHEET
- Individual pages for construction and electrical
- Individual pages for each floor

### Michael Smith 2
- All floors are on one page
- Construction and Electrical are different pages
- Page names contain a lot more ex "DEMOLITION PLANS & ELEVATIONS, CONSTRUCTION PLANS & SCHEDULES"
- Construction plans are labeled "FIRST FLOOR CONSTRUCTION PLAN"

### JPFranzen
- Just Construction. No Tables to parse
- Hexagons are windows
- Circles for doors
- Square with CL for closet
- Duplicate labels for different vantage points

### Lyons
- Window symbols and door symbols defined on first page
- More Legends on further pages
- Duplicates across pages for different vantage points


