

import debugutils
debugutils.set_is_dev()
import app # pylint:disable=wrong-import-position

def main():
  results = app.handler({
    "pdfId": "plan.pdf"
  }, None)
  print(results)

if __name__ == "__main__":
  main()
