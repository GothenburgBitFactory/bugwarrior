FAQ
===

Can bugwarrior support <some issue tracking system>?
----------------------------------------------------

Sure! But our general rule here is that we won't write a backend for a service
unless we use it personally, otherwise it's hard to be sure that it really
works.

We also try to rely on people to become maintainers of the different backend
plugins they use so that they don't suffer bit rot over time.

In summary, we need someone who 1) uses <some issue tracking system> and 2) can
develop the plugin.  Could it be you? :)

Does bugwarrior do two-way synchronization?
-------------------------------------------

No. Bugwarrior takes remote sources as the authoritative source of truth and
synchronizes your local taskwarrior database to align with the remote. Data from
taskwarrior is never pushed to remotes.
