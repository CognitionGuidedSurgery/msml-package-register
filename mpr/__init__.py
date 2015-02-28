__author__ = 'weigl'

import json
import jinja2
import re

import yaml
from path import Path
import click
import markdown

import mpr.config

jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))


class Package(object):
    def __init__(self):
        self.unique_name = None
        self.package_url = None
        self.readme_url = None
        self.repository_url = None
        self.website = None
        self.provider = None

        self.provider_logo = None

        self._meta = None
        self._content = None


    @property
    def readme_file(self):
        return self.folder / "README.md"

    @property
    def package_file(self):
        return self.folder / "msml-package.yaml"

    @property
    def folder(self):
        return PACKAGES_DIR / self.unique_name

    def __str__(self):
        return "Package: %s " % self.unique_name

    @property
    def meta(self):
        if not self._meta:
            with open(self.package_file) as fp:
                self._meta = yaml.load(fp)
        return self._meta

    @property
    def readme(self):
        if not self._content:
            with open(self.readme_file) as fp:
                self._content = fp.read()
        return self._content

    @property
    def html(self):
        return markdown.markdown(self.readme)

    @property
    def maintainer_without_email(self):
        m = str(self.meta.get('maintainer', "unknown"))
        pos = m.find("<")
        if pos > 0:
            m = m[:pos]
        return m


    @property
    def maintainer_as_link(self):
        m = self.meta.get('maintainer', "unknown")
        pos1 = m.find("<")
        pos2 = m.rfind(">")

        name = m
        email = ""
        if pos1 > 0:
            name = m[:pos1]

        if pos1 > 0 and pos2 > 0:
            email = m[pos1 + 1:pos2]

        return '<a href="mailto:%s">%s</a>' % (email, name)


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
        #click.echo("\twith package: %s" % package_url)
        #click.echo("\twith readme : %s" % readme_url)


def error(message):
    click.echo(click.style("ERROR: ", fg='red') + message, err=True)


def warning(message):
    click.echo(click.style("WARNING: ", fg='yellow') + message, err=True)


def do(message):
    click.echo(click.style(">>> ", fg='blue') + message, err=False)


def read_directory():
    return json.load(Path("./packages/directory.json").open())


def get_all_packages():
    handlers = {
        "gh:": GitHubPackage
    }

    for tok in read_directory():
        for h in handlers:
            if tok.startswith(h):
                yield handlers[h](tok)
                break


import requests

PACKAGES_DIR = Path("packages")


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
    packages = sorted(list(get_all_packages()),
                      cmp=lambda x, y: cmp(x.meta['name'], y.meta['name']))

    template = jinja_env.get_template("index.jinja2")
    render_template("index.html", template, packages=packages)

    package_template = jinja_env.get_template("package.jinja2")
    for package in packages:
        render_template(package.folder / "index.html",
                        package_template,
                        package=package)


