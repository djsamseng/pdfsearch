# Database Setup

## Supabase
### Database
```sql
CREATE TABLE IF NOT EXISTS pdf_summary (
  pdf_id TEXT PRIMARY KEY,
  pdf_summary JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS pdf_element_locations (
  pdf_id TEXT NOT NULL,
  element_type TEXT NOT NULL,
  on_page INT NOT NULL,
  element_idx INT NOT NULL,

  PRIMARY KEY(pdf_id, element_type, on_page, element_idx),
  FOREIGN KEY(pdf_id) REFERENCES pdf_summary(pdf_id)
);
CREATE TABLE IF NOT EXISTS pdf_processing_progress (
  pdf_id TEXT PRIMARY KEY,
  curr_step INT NOT NULL DEFAULT 0,
  total_steps INT NOT NULL,
  msg TEXT,
  success BOOLEAN
);
```

### Storage
- Click storage in the dashboard
- Create a public bucket (if going to production with supabase storage instead of S3 make it private and use createSignedUrl to send to lambda)
- Create a policy on the pdfs bucket allowing select insert and update for all users