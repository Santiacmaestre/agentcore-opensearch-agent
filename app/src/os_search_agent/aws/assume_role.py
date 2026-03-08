"""assume_role.py -- AssumeRoleSessionFactory for cross-account access.

Given an account_id + role_arn + region, produces a boto3 session whose
credentials are obtained via ``sts:AssumeRole``.
"""

from __future__ import annotations

import re
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from os_search_agent.aws.session_cache import SessionCache, get_default_cache

# -- ARN validation -----------------------------------------------------------

_ROLE_ARN_PATTERN = re.compile(
    r"^arn:aws(?:-cn|-us-gov)?:iam::\d{12}:role/[\w+=,.@/-]{1,512}$"
)

_ACCOUNT_ID_PATTERN = re.compile(r"^\d{12}$")


def validate_role_arn(role_arn: str) -> None:
    """Raise ``ValueError`` if *role_arn* does not match the expected format."""
    if not _ROLE_ARN_PATTERN.match(role_arn):
        raise ValueError(
            f"Invalid role ARN: '{role_arn}'.\n"
            "Expected format: arn:aws:iam::<12-digit-account-id>:role/<role-name>"
        )


def validate_account_id(account_id: str) -> None:
    """Raise ``ValueError`` if *account_id* is not a 12-digit string."""
    if not _ACCOUNT_ID_PATTERN.match(account_id):
        raise ValueError(
            f"Invalid account ID: '{account_id}'.  Must be exactly 12 digits."
        )


# -- Factory ------------------------------------------------------------------

class AssumeRoleSessionFactory:
    """Creates and caches boto3 sessions for cross-account roles."""

    def __init__(
        self,
        logger: object,
        session_duration_seconds: int = 3600,
        cache: Optional[SessionCache] = None,
        base_session: Optional[boto3.Session] = None,
    ) -> None:
        self._logger = logger
        self._duration = session_duration_seconds
        self._cache = cache or get_default_cache()
        self._base_session = base_session or boto3.Session()

    def get_session(
        self,
        account_id: str,
        role_arn: str,
        region: str,
        role_session_name: str = "os-search-agent",
    ) -> boto3.Session:
        """Return a boto3 session with credentials for *role_arn* in *region*."""
        validate_account_id(account_id)
        validate_role_arn(role_arn)

        cached = self._cache.get(role_arn, region)
        if cached:
            return cached

        sts = self._base_session.client("sts", region_name=region)
        try:
            resp = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName=role_session_name,
                DurationSeconds=self._duration,
            )
        except ClientError as exc:
            self._logger.error(  # type: ignore[attr-defined]
                "assume_role_failed",
                exc=exc,
                role_arn=role_arn,
                account_id=account_id,
                region=region,
            )
            raise

        creds = resp["Credentials"]
        expiration = creds["Expiration"]
        expires_at = expiration.timestamp()

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
        )

        self._cache.put(role_arn, region, session, expires_at)

        self._logger.info(  # type: ignore[attr-defined]
            "assumed_role",
            account_id=account_id,
            role_arn=role_arn,
            region=region,
            expires_at=expiration.isoformat(),
        )
        return session

    def get_client(
        self,
        service_name: str,
        account_id: str,
        role_arn: str,
        region: str,
    ) -> object:
        """Convenience shortcut: return a boto3 client for *service_name*."""
        session = self.get_session(account_id=account_id, role_arn=role_arn, region=region)
        return session.client(service_name, region_name=region)

    def build_env_vars(
        self,
        account_id: str,
        role_arn: str,
        region: str,
    ) -> dict[str, str]:
        """Return a dict of ``AWS_*`` env vars suitable for subprocess injection."""
        session = self.get_session(account_id=account_id, role_arn=role_arn, region=region)
        creds = session.get_credentials().get_frozen_credentials()
        return {
            "AWS_ACCESS_KEY_ID":     creds.access_key,
            "AWS_SECRET_ACCESS_KEY": creds.secret_key,
            "AWS_SESSION_TOKEN":     creds.token or "",
            "AWS_DEFAULT_REGION":    region,
        }
