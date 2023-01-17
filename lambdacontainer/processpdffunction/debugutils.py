

import os

def set_is_dev():
  # IMPORTANT - only set variables that are okay if hacked
  os.environ["DEV_LOCAL"] = "True"
  os.environ["SUPABASE_URL"] = "http://localhost:54321" # "http://host.docker.internal:54321"
  os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0" # pylint: disable=line-too-long

def is_dev():
  return "DEV_LOCAL" in os.environ
