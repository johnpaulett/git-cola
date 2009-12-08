from cola import gitcmd
from cola import gitcmds

git = gitcmd.instance()


def commits(max_count=808, log_args=None):
    if log_args is None:
        log_args = gitcmds.branch_list()
    log = git.log(topo_order=True,
                  # put subject at the end b/c it can contain
                  # any number of funky characters
                  pretty='format:%h%x00%p%x00%d%x00%an%x00%aD%x00%s',
                  max_count=max_count,
                  *log_args)
    return [Commit(log_entry=line) for line in log.splitlines()]


class Commit(object):
    def __init__(self, sha1='', log_entry=''):
        self.sha1 = sha1
        self.subject = ''
        self.parents = []
        self.tags = set()
        self.author = ''
        self.authdate = ''
        if log_entry:
            self.parse(log_entry)

    def parse(self, log_entry):
        self.sha1, parents, tags, author, authdate, subject = \
                log_entry.split('\0', 5)
        if subject:
            self.subject = subject
        if parents:
            for parent in parents.split(' '):
                self.parents.append(parent)
        if tags:
            for tag in tags[2:-1].split(', '):
                if tag.startswith('tag: '):
                    tag = tag[10:] # tag: refs/
                elif tag.startswith('refs/remotes/'):
                    tag = tag[13:] # refs/remotes/
                elif tag.startswith('refs/heads/'):
                    tag = tag[11:] # refs/heads/
                else:
                    tag = tag[5:] # refs/
                self.tags.add(tag)
        if author:
            self.author = author
        if authdate:
            self.authdate = authdate

        return self

    def __repr__(self):
        return ("{\n"
                "  sha1: " + self.sha1 + "\n"
                "  subject: " + self.subject + "\n"
                "  author: " + self.author + "\n"
                "  authdate: " + self.authdate + "\n"
                "  parents: [" + ', '.join(self.parents) + "]\n"
                "  tags: [" + ', '.join(self.tags) + "]\n"
                "}")
