import argparse
import jinja2 as jinja
from abgrid.ABGridDocuments import ABGridDocuments
from abgrid.ABGridData import ABGridData
from abgrid.ABGridYAML import ABGridYAML

# set jinja
jinja_env = jinja.Environment(loader=jinja.FileSystemLoader("./abgrid/templates"))

parser = argparse.ArgumentParser(
    prog="ABGrid",
    description="Generate ABGrid files",
    epilog="Text at the bottom of help")

parser.add_argument("-a", "--action", required=True, help="scegli nome progetto")
parser.add_argument("-p", "--project_name", required=True, help="scegli nome progetto")
parser.add_argument("-g", "--n_groups", help="numero gruppi")
parser.add_argument("-m", "--n_members_per_group",  help="numero membri per gruppi")
args = parser.parse_args()

if args.action == "init":
  ABGridDocuments.init_files(args.project_name, args.n_groups, args.n_members_per_group, jinja_env)
else:
  abgrid_data = ABGridData(args.project_name, ABGridYAML())
  abgrid_documents = ABGridDocuments(abgrid_data, jinja_env)
  abgrid_documents.generate_answer_sheets() if args.action == "sheets" else abgrid_documents.generate_reports()
  