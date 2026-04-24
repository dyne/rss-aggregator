## Contributing

If you make changes to Venus, you have no obligation to share them. And unlike systems based on `CVS` or `subversion`, there is no notion of “committers” — everybody is a peer.

If you should chose to share your changes, the steps outlined below may increase your changes of your code being picked up.

### Documentation and Tests

For best results, include both documentation and tests in your contribution.

Documentation can be found in the `docs` directory. It is written in Markdown.

Test cases can be found in the [tests](http://intertwingly.net/code/venus/tests/) directory. The maintained runner is [pytest](https://docs.pytest.org/), while most existing test modules still use unittest-style classes under pytest collection. To run them, simply enter:

>     uv run pytest

To run one module:

>     uv run pytest tests/test_storage.py

To generate a local coverage report:

>     uv run pytest --cov=src --cov-report=term-missing --cov-report=xml

If you want quick coverage gains without broad fixture churn, prefer small
deterministic modules first: `src/storage.py`, `src/output.py`,
`src/media.py`, `src/expunge.py`, and `src/config.py`.

Install development dependencies from the lock file before testing:

>     uv sync

### Git

If you have already pulled the repository, the only additional step you might need is to introduce yourself to [git](http://git-scm.com/). Type in the following, after replacing the **bold text** with your information:

>     git config --global user.name 'Your Name'
>     git config --global user.email 'youremail@example.com'

Then, simply make the changes you like. When you are done, type:

>     git status

This will tell you which files you have modified, and which ones you may have added. If you add files and you want them to be included, simply do a:

>     git add file1 file2...

You can also do a `git diff` to see if there are any changes which you made that you don't want included. I can't tell you how many debug print statements I have caught this way.

Next, type:

>     git commit -a

This will allow you to enter a comment describing your change. If your repository is already on your web server, simple let others know where they can find it. If not, consider using [github]() to host your [fork](http://help.github.com/forking/) of Venus.

### Telling others

Once you have a change worth sharing, post a message on the [mailing list](http://lists.planetplanet.org/mailman/listinfo/devel), or use github to send a [pull request](http://github.com/guides/pull-requests).
