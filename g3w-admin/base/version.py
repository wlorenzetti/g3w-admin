import os
import subprocess
import datetime


def get_version(version=None):
    """
    Returns a PEP 386-compliant version number from VERSION.

    from geonode: https://github.com/GeoNode/geonode/blob/master/geonode/version.py
    """

    if version is None:
        from base import __version__ as version
    else:
        assert len(version) == 5
        assert version[3] in ('unstable', 'beta', 'rc', 'final')

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|c}N - for alpha, beta and rc releases

    parts = 2 if version[2] == 0 else 3
    #main = '.'.join(str(x) for x in version[:parts])
    main = ''

    sub = ''
    if version[3] == 'unstable':
        git_changeset = get_git_changeset()
        git_branch = get_git_branch()
        if git_changeset:
            dot = '.' if main else ''
            sub = '%s%s-%s' % (dot, git_branch, git_changeset)

    elif version[3] != 'final':
        mapping = {'beta': 'b', 'rc': 'rc'}
        sub = mapping[version[3]] + str(version[4])

    return main + sub


def get_git_branch():
    """ Return current git code branch """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_branch = subprocess.Popen('git branch',
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True, cwd=repo_dir, universal_newlines=True)
    branches = git_branch.communicate()[0].split('\n')
    return [b for b in branches if b.startswith('*')][0][2:]


def get_git_changeset():
    """Returns a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.

    from geonode: https://github.com/GeoNode/geonode/blob/master/geonode/version.py
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_show = subprocess.Popen('git show --pretty=format:%ct --quiet HEAD',
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True, cwd=repo_dir, universal_newlines=True)
    timestamp = git_show.communicate()[0].partition('\n')[0]
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        return None
    return timestamp.strftime('%Y%m%d%H%M%S')