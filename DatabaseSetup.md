# Database Setup

## Supabase
### Database

#### No users
```sql


-- All timestamps are UTC

CREATE TABLE IF NOT EXISTS pdfs (
  pdf_id TEXT NOT NULL,
  pdf_name TEXT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT now(),

  PRIMARY KEY(pdf_id)
);
CREATE TABLE IF NOT EXISTS pdf_versions(
  pdf_id TEXT REFERENCES pdfs(pdf_id) NOT NULL,
  version INT4 NOT NULL,
  last_accessed TIMESTAMP DEFAULT now(),
  last_modified TIMESTAMP DEFAULT now(),
  data JSON,

  PRIMARY KEY(pdf_id, version)
);

CREATE TABLE IF NOT EXISTS elems (
  id UUID PRIMARY KEY,
  pdf_id TEXT REFERENCES pdfs(pdf_id) NOT NULL,
  bbox float4 ARRAY NOT NULL,
  page_number INT4 NOT NULL,
  data json NOT NULL,
  elem_type TEXT NOT NULL
);
CREATE INDEX elems_by_pdf ON elems(pdf_id, page_number);

CREATE TABLE IF NOT EXISTS links (
  from_id UUID REFERENCES elems(id) NOT NULL,
  to_id UUID REFERENCES elems(id) NOT NULL,
  link_type TEXT NOT NULL,

  PRIMARY KEY(from_id, link_type, to_id)
);

CREATE INDEX links_to_type_from ON links(to_id, link_type, from_id);

INSERT INTO storage.buckets (id, name, public)
  VALUES ("public_pdfs", "public pdfs", true);
CREATE POLICY "public_pdfs viewable by all" ON storage.objects
  for SELECT with check (bucket_id = "public_pdfs");
CREATE POLICY "public_pdfs insert by all" ON storage.objects
  for INSERT with check (bucket_id = "public_pdfs");
CREATE POLICY "public_pdfs update by all" ON storage.objects
  for UPDATE with check (bucket_id = "public_pdfs");

CREATE TABLE IF NOT EXISTS pdf_processing_progress (
  pdf_id TEXT PRIMARY KEY,
  curr_step INT NOT NULL DEFAULT 0,
  total_steps INT NOT NULL,
  msg TEXT,
  success BOOLEAN
);

```


#### With Users
- [https://supabase.com/docs/guides/getting-started/tutorials/with-nextjs#set-up-the-database-schema](https://supabase.com/docs/guides/getting-started/tutorials/with-nextjs#set-up-the-database-schema)
```sql
CREATE TABLE IF NOT EXISTS pdf_summary (
  pdf_id TEXT PRIMARY KEY,
  pdf_name TEXT NOT NULL,
  pdf_summary JSON
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

-- All timestamps are UTC
CREATE TABLE IF NOT EXISTS profiles (
  id UUID REFERENCES auth.users NOT NULL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW(),
  first_name TEXT DEFAULT "",
  last_name TEXT DEFAULT ""
);
CREATE TABLE IF NOT EXISTS pdfs (
  owner_id UUID REFERENCES profiles(id) NOT NULL,
  pdf_id TEXT NOT NULL,
  pdf_name TEXT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT now(),

  PRIMARY KEY(owner_id, pdf_id)
);
CREATE TABLE IF NOT EXISTS pdf_versions(
  owner_id UUID REFERENCES profiles(id) NOT NULL,
  pdf_id TEXT REFERENCES pdfs(pdf_id) NOT NULL,
  version INT4 NOT NULL,
  last_accessed TIMESTAMP DEFAULT now(),
  last_modified TIMESTAMP DEFAULT now(),
  data JSON,

  PRIMARY KEY(owner_id, pdf_id, version)
);

CREATE TABLE IF NOT EXISTS elems (
  id UUID PRIMARY KEY,
  owner_id UUID REFERENCES profiles(id) NOT NULL,
  pdf_id TEXT REFERENCES pdfs(pdf_id) NOT NULL,
  bbox float4 ARRAY NOT NULL,
  page_number INT4 NOT NULL,
  data json NOT NULL,
  elem_type TEXT NOT NULL
);
CREATE INDEX elems_by_pdf ON elems(owner_id, pdf_id, page_number);

CREATE TABLE IF NOT EXISTS links (
  from_id UUID REFERENCES elems(id) NOT NULL,
  to_id UUID REFERENCES elems(id) NOT NULL,
  link_type TEXT NOT NULL,

  PRIMARY KEY(from_id, link_type, to_id)
);

CREATE INDEX links_to_type_from ON links(to_id, link_type, from_id);

ALTER TABLE profiles
  enable row level security;
CREATE POLICY "Profiles viewable by owner" ON profiles
  for SELECT with check (auth.uid() = id)
CREATE POLICY "Users insert their own profile" ON profiles
  for INSERT with check (auth.uid() = id)
CREATE POLICY "Users update their own profile" ON profiles
  for UPDATE with check (auth.uid() = id)

-- This trigger automatically creates a profile entry when a new user signs up via Supabase Auth.
-- See https://supabase.com/docs/guides/auth/managing-user-data#using-triggers for more details.
create function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, first_name, last_name)
  values (new.id, new.raw_user_meta_data->>'first_name', new.raw_user_meta_data->>'last_name');
  return new;
end;

$$ language plpgsql security definer;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

INSERT INTO storage.buckets (id, name, public)
  VALUES ("pdfs", "pdfs", false)
CREATE POLICY "pdfs viewable by owner" ON storage.objects
  for SELECT using (auth.uid() = owner) with check (bucket_id = "pdfs")
CREATE POLICY "Users insert their pdfs" ON profiles
  for INSERT using (auth.uid() = owner) with check (bucket_id = "pdfs")
CREATE POLICY "Users update their pdfs" ON profiles
  for UPDATE using (auth.uid() = owner) with check (bucket_id = "pdfs")

INSERT INTO storage.buckets (id, name, public)
  VALUES ("public_pdfs", "public pdfs", true)
CREATE POLICY "public_pdfs viewable by all" ON storage.objects
  for SELECT with check (bucket_id = "pdfs")
CREATE POLICY "public_pdfs insert by all" ON profiles
  for INSERT with check (bucket_id = "pdfs")
CREATE POLICY "public_pdfs update by all" ON profiles
  for UPDATE with check (bucket_id = "pdfs")

```

### Realtime Database Updates
```sql
begin;
  -- remove the supabase_realtime publication
  drop publication if exists supabase_realtime;

  -- re-create the supabase_realtime publication with no tables and only for update
  create publication supabase_realtime with (publish = 'update');
commit;

-- add a table to the publication
alter publication supabase_realtime add table pdf_processing_progress;
```

### Storage
- Click storage in the dashboard
- Create a public bucket "pdfs" (if going to production with supabase storage instead of S3 make it private and use createSignedUrl to send to lambda)
- Create a policy on the pdfs bucket allowing select insert and update for all users