
import os

import pdfminer.high_level

os.environ["DEV_LOCAL"] = "True"
os.environ["SUPABASE_URL"] = "http://host.docker.internal:54321"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

import pdfprocessor

def main():
  pages_gen = pdfminer.high_level.extract_pages(pdf_file="plan.pdf", page_numbers=[9])
  processor = pdfprocessor.PdfProcessor(pages_gen=pages_gen)
  for idx, _ in enumerate(processor.process_page()):
    print("Processing page: {0}".format(idx+1))

if __name__ == "__main__":

  main()