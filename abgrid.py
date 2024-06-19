import argparse
import jinja2 as jinja
from abgrid.ABGridDocuments import ABGridDocuments
from abgrid.ABGridData import ABGridData
from abgrid.ABGridYAML import ABGridYAML

jinja_env = jinja.Environment(
    loader=jinja.FileSystemLoader([ "./abgrid/templates", "./templates" ]))

parser = argparse.ArgumentParser(prog="ABGrid")
parser.add_argument("-a", "--action", required=True, choices=["init", "sheets", "reports"])
parser.add_argument("-p", "--project_name", required=True,)
parser.add_argument("-g", "--n_groups", type=int, choices=range(1, 21))
parser.add_argument("-m", "--n_members_per_group", type=int, choices=range(3, 16))
args = parser.parse_args()

if args.action == "init":
  if not args.n_groups or not args.n_members_per_group:
    print("Please specify the following parameters: project_name (-p), n_groups (-g), n_members_per_group (-m)")
  else:
    ABGridDocuments.init_files(
        args.project_name, args.n_groups, args.n_members_per_group, jinja_env)
else:
  abgrid_data = ABGridData(args.project_name, ABGridYAML())
  abgrid_documents = ABGridDocuments(abgrid_data, jinja_env)
  abgrid_documents.generate_answer_sheets(
  ) if args.action == "sheets" else abgrid_documents.generate_reports()
