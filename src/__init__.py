"""Flask app config and initialization"""
import logging.config
from flask import Flask


def create_app(config_obj=None):
    app = Flask(__name__)

    if not config_obj:
        logging.warning("No config specified; defaulting to development")

        import config
        config_obj = config.DevelopmentConfig

    app.config.from_object(config_obj)

    # CORS allow
    from flask_cors import CORS
    cors = CORS(app, resources={r"/api/*": {"origins": "*"}})

    # DB service
    from src.services.db import db
    db.init_app(app)
    db.app = app

    # Migration service
    from src.services.migrate import migrate
    migrate.init_app(app, db)

    # Marshmallow service
    from src.services.marshmallow import ma
    ma.init_app(app)

    # JWT service
    from src.services.jwt import jwt
    jwt.init_app(app)

    # Router service
    from src.routes import api_router
    api_router.init_app(app)

    from src.resources.auth import SignInResource, SignUpResource, SignOutResource, TokenRefreshResource,\
        UserVerifyResource, ResendVerifyEmailResource, UpdateEmailResource
    api_router.add_resource(SignInResource, "/auth/sign-in")
    api_router.add_resource(SignUpResource, "/auth/sign-up")
    api_router.add_resource(SignOutResource, "/auth/sign-out")
    api_router.add_resource(TokenRefreshResource, "/auth/refresh")
    api_router.add_resource(UserVerifyResource, "/auth/email/verify", methods=['POST'])
    api_router.add_resource(ResendVerifyEmailResource, "/auth/email/resend", methods=['POST'])
    api_router.add_resource(UpdateEmailResource, "/auth/email/update", methods=['POST'])

    from src.resources.profile import GetProfileResource, UpdateProfileResource, \
        PasswordResetResource, CloseProfileResource, ProfileImageResource
    api_router.add_resource(GetProfileResource, "/profile", methods=['GET'])
    api_router.add_resource(UpdateProfileResource, "/profile", methods=['PUT'])
    api_router.add_resource(PasswordResetResource, "/profile/password-reset", methods=['POST'])
    api_router.add_resource(CloseProfileResource, "/profile/close", methods=['POST'])
    api_router.add_resource(ProfileImageResource, "/profile/image", methods=['POST'])

    from src.resources.users import GetUserResource, GetUsersResource, \
        UpdateUserResource, DeleteUserResource
    api_router.add_resource(GetUsersResource, "/users", methods=['GET'])
    api_router.add_resource(GetUserResource, "/users/<id>", methods=['GET'])
    api_router.add_resource(UpdateUserResource, "/users/<id>", methods=['PUT'])
    api_router.add_resource(DeleteUserResource, "/users/<id>", methods=['DELETE'])

    from src.resources.episodes import GetEpisodeResource, GetEpisodesResource, \
        CreateEpisodesResource, UpdateEpisodesResource, DeleteEpisodesResource
    api_router.add_resource(CreateEpisodesResource, "/episodes", methods=['POST'])
    api_router.add_resource(GetEpisodesResource, "/episodes", methods=['GET'])
    api_router.add_resource(GetEpisodeResource, "/episodes/<user_id>/<id>", methods=['GET'])
    api_router.add_resource(UpdateEpisodesResource, "/episodes/<id>", methods=['PUT'])
    api_router.add_resource(DeleteEpisodesResource, "/episodes/<id>", methods=['DELETE'])

    from src.resources.s3upload import S3SignedDataResource
    api_router.add_resource(S3SignedDataResource, "/s3upload", methods=['POST', 'PUT'])

    from src.resources.authorized_users import GetAuthorizedUsersResource, GetAuthorizedUserResource, \
        CreateAuthorizedUserResource, UpdateAuthorizedUserResource, DeleteAuthorizedUserResource, \
        InviteAuthorizedUserResource, AuthorizeUserResource
    api_router.add_resource(CreateAuthorizedUserResource, "/authorized-users", methods=['POST'])
    api_router.add_resource(GetAuthorizedUsersResource, "/authorized-users", methods=['GET'])
    api_router.add_resource(GetAuthorizedUserResource, "/authorized-users/<id>", methods=['GET'])
    api_router.add_resource(UpdateAuthorizedUserResource, "/authorized-users/<id>", methods=['PUT'])
    api_router.add_resource(DeleteAuthorizedUserResource, "/authorized-users/<id>", methods=['DELETE'])
    api_router.add_resource(InviteAuthorizedUserResource, "/authorized-users/invite/<id>", methods=['GET'])
    api_router.add_resource(AuthorizeUserResource, "/studio/authorize", methods=['POST'])

    from src.resources.media_objects import GetMediaObjectsResource, GetMediaObjectResource, \
        CreateMediaObjectResource, UpdateMediaObjectResource, DeleteMediaObjectResource, UploadMediaObjectsResource
    api_router.add_resource(CreateMediaObjectResource, "/media-objects", methods=['POST'])
    api_router.add_resource(GetMediaObjectsResource, "/media-objects", methods=['GET'])
    api_router.add_resource(GetMediaObjectResource, "/media-objects/<id>", methods=['GET'])
    api_router.add_resource(UpdateMediaObjectResource, "/media-objects/<id>", methods=['PUT'])
    api_router.add_resource(DeleteMediaObjectResource, "/media-objects/<id>", methods=['DELETE'])
    api_router.add_resource(UploadMediaObjectsResource, "/media-objects/bulk-upload", methods=['POST'])

    from src.resources.uploading_platforms import GetUploadingPlatformsResource, GetUploadingPlatformResource, \
        CreateUploadingPlatformResource, UpdateUploadingPlatformResource, DeleteUploadingPlatformResource
    api_router.add_resource(CreateUploadingPlatformResource, "/uploading-platforms", methods=['POST'])
    api_router.add_resource(GetUploadingPlatformsResource, "/uploading-platforms", methods=['GET'])
    api_router.add_resource(GetUploadingPlatformResource, "/uploading-platforms/<id>", methods=['GET'])
    api_router.add_resource(UpdateUploadingPlatformResource, "/uploading-platforms/<id>", methods=['PUT'])
    api_router.add_resource(DeleteUploadingPlatformResource, "/uploading-platforms/<id>", methods=['DELETE'])

    from src.resources.streaming_platforms import GetStreamingPlatformsResource, GetStreamingPlatformResource, \
        CreateStreamingPlatformResource, UpdateStreamingPlatformResource, DeleteStreamingPlatformResource
    api_router.add_resource(CreateStreamingPlatformResource, "/streaming-platforms", methods=['POST'])
    api_router.add_resource(GetStreamingPlatformsResource, "/streaming-platforms", methods=['GET'])
    api_router.add_resource(GetStreamingPlatformResource, "/streaming-platforms/<id>", methods=['GET'])
    api_router.add_resource(UpdateStreamingPlatformResource, "/streaming-platforms/<id>", methods=['PUT'])
    api_router.add_resource(DeleteStreamingPlatformResource, "/streaming-platforms/<id>", methods=['DELETE'])

    from src.resources.oauth_tokens import OAuthTokenResource
    api_router.add_resource(OAuthTokenResource, "/oauth-tokens", methods=['POST'])

    from src.resources.media_configuration import CreateMediaConfigurationResource, UpdateMediaConfigurationResource, \
        GetMediaConfigurationsResource, GetMediaConfigurationResource, DeleteMediaConfigurationResource, \
        GetMediaURLsResource, LoadMediaConfigurationResource
    api_router.add_resource(CreateMediaConfigurationResource, "/media-configuration", methods=['POST'])
    api_router.add_resource(GetMediaConfigurationsResource, "/media-configuration", methods=['GET'])
    api_router.add_resource(GetMediaConfigurationResource, "/media-configuration/<user_id>", methods=['GET'])
    api_router.add_resource(UpdateMediaConfigurationResource, "/media-configuration/<id>", methods=['PUT'])
    api_router.add_resource(DeleteMediaConfigurationResource, "/media-configuration/<id>", methods=['DELETE'])
    api_router.add_resource(GetMediaURLsResource, "/media/urls", methods=['GET'])
    api_router.add_resource(LoadMediaConfigurationResource, "/media/configuration/<user_id>", methods=['GET'])

    api_router.register_routes()

    return app
