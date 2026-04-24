## Etiquette

You would think that people who publish syndication feeds do it with the intent to be syndicated. But the truth is that we live in a world where [deep linking](http://en.wikipedia.org/wiki/Deep_linking) can cause people to complain. Nothing is safe. But that doesn’t stop us from doing links.

These concerns tend to increase when you profit, either directly via ads or indirectly via search engine rankings, from the content of others.

While there are no hard and fast rules that apply here, here’s are a few things you can do to mitigate the concern:

Aggressively use robots.txt, meta tags, and the google/livejournal atom namespace to mark your pages as not to be indexed by search engines.

> [robots.txt](http://www.robotstxt.org/):  
> `User-agent: *`  
> `Disallow: /`
>
> index.html:  
> `<`[`meta name="robots"`](http://www.robotstxt.org/wc/meta-user.html)` content="noindex,nofollow"/>`
>
> aggregated feed:  
> `<feed xmlns:indexing="`[`urn:atom-extension:indexing`](http://community.livejournal.com/lj_dev/696793.html)`" indexing:index="no">`
>
> `<access:restriction xmlns:access="`[`http://www.bloglines.com/about/specs/fac-1.0`](http://www.bloglines.com/about/specs/fac-1.0)`" relationship="deny"/>`

Ensure that all [copyright](http://nightly.feedparser.org/docs/reference-entry-source.html#reference.entry.source.rights) and [licensing](http://nightly.feedparser.org/docs/reference-entry-license.html) information is propagated to the combined feed(s) that you produce.

Add no advertising. Consider filtering out ads, lest you be accused of using someone’s content to help your friends profit.

Most importantly, if anyone does object to their content being included, quickly and without any complaint, remove them.
