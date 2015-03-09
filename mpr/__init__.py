import markdown

__author__ = 'weigl'

import json
import re

import jinja2
from path import Path
import click
import requests
from path import path

from msml.package import Repository, Package
import mpr.config

jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))


def html(package):
    if package.information.documentation.file:
        md = path(package.base_path) / package.information.documentation.file
        return markdown.markdown(md)
    elif package.information.documentation.content:
        return markdown.markdown(package.information.documentation.content)
    return ""


def url(package):
    return "%s/p/%s.html" % (mpr.config.BASE_PATH, package.name)



jinja_env.filters['html'] = html
jinja_env.filters['url'] = url


class GitHubPackage(Package):
    def __init__(self, tok):
        super(GitHubPackage, self).__init__()

        self.provider_logo = mpr.config.BASE_PATH + "/assets/GitHub-Mark-32px.png"

        values = re.compile(r'gh:([^/]+)/([^/]+)').findall(tok)
        user, name = values[0]
        self.unique_name = user + "_" + name
        self.repository_url = "https://github.com/{user}/{name}.git".format(user=user, name=name)
        self.package_url = "https://raw.githubusercontent.com/{user}/{name}/master/msml-package.yaml".format(user=user,
                                                                                                             name=name)
        self.readme_url = "https://raw.githubusercontent.com/{user}/{name}/master/README.md".format(user=user,
                                                                                                    name=name)
        self.website = "https://github.com/{user}/{name}".format(user=user, name=name)
        self.provider = "github"

        self.user = user
        self.name = name

        # click.echo("Package: %s" % name)
        # click.echo("\twith repo   : %s" % repository_url)
        # click.echo("\twith package: %s" % package_url)
        # click.echo("\twith readme : %s" % readme_url)


def error(message):
    click.echo(click.style("ERROR: ", fg='red') + message, err=True)


def warning(message):
    click.echo(click.style("WARNING: ", fg='yellow') + message, err=True)


def do(message):
    click.echo(click.style(">>> ", fg='blue') + message, err=False)


def read_directory():
    return json.load(Path("./packages/directory.json").open())


def download_file(url, filename):
    response = requests.get(url)

    do("Download %s" % url)

    if response.status_code == 200:
        with open(filename, 'w') as fp:
            fp.write(response.content)
    else:
        error("%s returned %d" % (url, response.status_code))


def get_defaults():
    import mpr.config

    return mpr.config.__dict__


def render_template(tofile, template, **kwargs):
    with open(tofile, 'w') as fp:
        k = get_defaults()
        k.update(kwargs)
        fp.write(template.render(**k))


def download_meta_data():
    for package in get_all_packages():
        folder = package.folder
        folder.makedirs_p()
        download_file(package.package_url, package.package_file)
        download_file(package.readme_url, package.readme_file)


def render_page():
    repo = Repository.from_file(".")
    packages = repo.resolve_packages()
    packages = sorted(packages,
                      cmp=lambda x, y: cmp(x.name, y.name))

    for p in packages:
        print "Found %s in %s" % (p, p.base_path)

    template = jinja_env.get_template("index.jinja2")
    render_template("index.html", template, packages=packages)

    package_template = jinja_env.get_template("package.jinja2")
    path("p").mkdir()
    for package in packages:
        render_template("p/%s.html" % package.name,
                        package_template,
                        package=package)


