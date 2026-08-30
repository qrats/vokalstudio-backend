![tests](https://github.com/qrats/vokalstudio-backend/workflows/tests/badge.svg)

## Vokal Studio

The API behind Vokal Studio: a browser recording studio that takes a live
session, restreams it to YouTube, Facebook, Twitch or a custom RTMP endpoint,
renders the recording into an episode, and pushes that episode out to podcast
directories.

### Layout

    app.py                the Flask entry point and the celery cli commands
    config.py             environment configuration
    src/models            SQLAlchemy models
    src/schemas           marshmallow schemas
    src/resources         flask-restful resources, grouped by area
    src/services          db, jwt, marshmallow, migrate and swagger wiring
    src/tasks             celery workers for media and episodes
    src/utils             paypal, s3, email and restream server helpers
    src/domain            the rules, with no framework attached
    tests                 the domain test suite
    migrations            alembic revisions

`src/domain` is where the parts worth arguing about live — billing proration,
the restream fan-out plan, loudness limiting, entitlement checks, the
publishing state machine. It has no dependency on Flask or the database, so it
can be read and tested on its own. See [docs/Domain.md](docs/Domain.md).

### Running the tests

    python -m unittest discover -s tests -t .

The suite is stdlib only. CI runs it on 3.9, 3.11 and 3.12 with no install
step, and `scripts/check_domain.py` fails the build if anything under
`src/domain` grows an import of Flask, SQLAlchemy, boto3, celery or requests.

### Running the service

    pip install -r requirements.txt
    flask db upgrade
    python app.py

The worker needs redis:

    celery -A app.celery worker --loglevel=info

### Deployment

Pushes to `master` deploy over ssh. The deploy job only runs when the
`DEPLOY_ENABLED` repository variable is set to `true`, so a fork or a checkout
without the deploy secrets reports the job as skipped rather than failed.

- apt install nginx
- apt install supervisor
- apt install redis

### API documentation

- [Authentication](docs/Authentication.md)
- [Authorized users](docs/Authorized_User.md)
- [Profile](docs/Profile.md)
- [The domain layer](docs/Domain.md)
