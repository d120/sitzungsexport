from re import compile, sub, findall
from typing import Match


def frontmatter(text: str, **replacements) -> str:
    template = """<table class="table" style="max-width: 300px; float: right; margin: 0 0 1rem 1rem; border: 1px solid #ddd">
  <thead>
    <tr><th colspan="2" class="text-center">Protokoll</th></tr>
  </thead>
  <tbody>
    <tr><td colspan="2" class="text-center">Fachschaftssitzung</td></tr>
    <tr><td>Datum</td><td class="text-right">{datum}</td></tr>
    <tr><td>Zeit</td><td class="text-right">{zeit}</td></tr>
    <tr><td>Protokollant*in</td><td class="text-right">{protokoll}</td></tr>
    <tr><td>Redeleitung</td><td class="text-right">{redeleitung}</td></tr>
    <tr><td>Anwesende</td><td class="text-right">{anwesende}</td></tr>
    <tr><td>Anwesende online:</td><td class="text-right">{online}</td></tr>
  </tbody>
</table>\n\n"""

    return template.format(**replacements) + text


def vote(text: str) -> str:
    template = """<table class="table" style="border: 1px solid #ddd;">
  <thead>
    <tr><th colspan="3" class="text-center">{borm}</th></tr>
  </thead>
  <tbody>
    <tr><td colspan="3"><i>
    {text}
    </i></td></tr>
    <tr>
      <th class="text-center">Ja</th>
      <th class="text-center">Nein</th>
      <th class="text-center">Enthaltung</th>
    </tr>
    <tr>
      <td class="text-center">{ja}</td>
      <td class="text-center">{nein}</td>
      <td class="text-center">{enthaltung}</td>
    </tr>
  </tbody>
</table>\n\n"""
    vote_regex = compile(
        "\[(?P<borm>beschluss|meinungsbild) text='(?P<text>.*)',\s+ja=(?P<ja>\d*),\s+nein=(?P<nein>\d*),\s+enthaltung=(?P<enthaltung>\d*)]"
    )
    votes = vote_regex.finditer(text)
    for vote in votes:
        text = text.replace(
            vote[0],
            template.format(
                borm=vote.group("borm").capitalize(),
                text=vote.group("text"),
                ja=vote.group("ja"),
                nein=vote.group("nein"),
                enthaltung=vote.group("enthaltung"),
            ),
        )
    return text


def gendern(text: str) -> str:
    return sub("(\w)(\*)(\w)", "\g<1>\*\g<3>", text)


def fix_indentation(text: str) -> str:

    def replacement_callback(match: Match) -> str:
        pattern = match.group(0)
        # replace additional tabstop
        pattern = pattern.replace("\t*", "*")
        # replace all other tabstops with two spaces
        return pattern.replace("\t", "  ")

    # remove all single indentations
    text = sub("\n\t*\*", replacement_callback, text)
    return text
