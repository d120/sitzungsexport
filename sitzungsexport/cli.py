import click
from sitzungsexport.bookstack import BookstackAPI
from sitzungsexport.models import Protocol

from datetime import date, datetime
from os import environ

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    pass


@cli.command("post", help="Post protocol on server")
@click.option("--url", help="URL of the bookstack instance", required=True)
@click.option("--username", "-u", help="Bookstack user", required=True)
@click.option("--password", "-p", help="Bookstack password", required=True)
@click.argument("protocolfile", type=click.File("r"))
def post(url: str, username: str, password: str, protocolfile):
    api = BookstackAPI(url, username, password)
    protocol = Protocol(protocolfile.read())
    date_str = protocol.frontmatter.get(
        "datum", str(date.today().strftime("%d.%m.%Y"))).strip()
    date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
    api.save_protocol(protocol, date_obj)


@cli.command("preview", help="Render a preview of the protocol")
@click.argument("protocolfile", type=click.File("r"))
def preview(protocolfile):
    protocol = Protocol(protocolfile.read())
    print(protocol.compile())


if __name__ == "__main__":
    cli(auto_envvar_prefix="BOOKSTACK")
