"""Vokal Studio domain layer.

Everything under ``src.domain`` is plain Python: no Flask, no SQLAlchemy, no
network access and no reads of the wall clock.  The Flask resources in
``src.resources`` stay responsible for HTTP and persistence; they hand rows to
``src.domain.adapters`` and get back value objects that can be reasoned about
and tested in isolation.

The layer is organised as follows::

    core          errors, guards, ids, text, collections, results
    timeline      instants, durations, timecode, intervals, calendars
    money         currencies, amounts, rounding, allocation, tax
    catalog       products, plans, features, entitlements, quotas
    billing       subscriptions, cycles, payments, invoices, dunning
    access        roles, permissions, grants, invitations, sessions
    media         assets, formats, loudness, renditions, configuration
    episodes      episodes, chapters, show notes, series, publishing
    streaming     platforms, RTMP targets, restream plans, live sessions
    servers       instance types, pools, allocation, provisioning
    distribution  destinations, credentials, upload jobs, feeds
    content       blog posts, markup, taxonomy, search
    analytics     play events, rollups, retention, reports
    adapters      translation to and from ORM rows and provider payloads
"""

__all__ = ["VERSION"]

VERSION = "1.0.0"
