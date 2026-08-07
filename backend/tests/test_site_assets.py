import pytest

from backend.app.site_assets import (
    CameraSource,
    CameraSourceKind,
    SiteMapAsset,
    SiteProfile,
)


def test_accepts_independent_verified_map_assets_for_office_and_dealer_sites():
    office = SiteProfile(
        site_id="huaxiang-office",
        display_name="Huaxiang Office",
        map_asset=SiteMapAsset(
            site_id="huaxiang-office",
            map_identity="hxzx-office-20260806",
            package_sha256="a" * 64,
            verified_on="2026-08-06",
        ),
        cameras=(),
    )
    dealer = SiteProfile(
        site_id="dongguan-mercedes",
        display_name="Dongguan Mercedes",
        map_asset=SiteMapAsset(
            site_id="dongguan-mercedes",
            map_identity="dg-mercedes-20260820",
            package_sha256="b" * 64,
            verified_on="2026-08-20",
        ),
        cameras=(),
    )

    assert office.map_asset.map_identity != dealer.map_asset.map_identity
    assert office.map_asset.package_sha256 != dealer.map_asset.package_sha256


def test_rejects_unverified_or_placeholder_map_evidence():
    with pytest.raises(ValueError, match="map_identity"):
        SiteMapAsset(site_id="office", map_identity="REPLACE_WITH_SITE_VALUE", package_sha256="a" * 64, verified_on="2026-08-06")

    with pytest.raises(ValueError, match="SHA-256"):
        SiteMapAsset(site_id="office", map_identity="office-map", package_sha256="not-a-hash", verified_on="2026-08-06")

    with pytest.raises(ValueError, match="different site"):
        SiteProfile(
            site_id="dongguan-mercedes",
            display_name="Dongguan Mercedes",
            map_asset=SiteMapAsset(
                site_id="huaxiang-office",
                map_identity="office-map",
                package_sha256="a" * 64,
                verified_on="2026-08-06",
            ),
            cameras=(),
        )


def test_camera_source_requires_site_verification_before_it_is_enabled():
    pending = CameraSource(
        name="front-body",
        kind=CameraSourceKind.ROBOT_BODY,
        stream_uri="rtsp://10.21.31.103:8554/video1",
        verified=False,
        verified_on=None,
    )
    assert pending.is_available is False

    source = CameraSource(
        name="rear-body",
        kind=CameraSourceKind.ROBOT_BODY,
        stream_uri="rtsp://10.21.31.103:8554/video2",
        verified=True,
        verified_on="2026-08-06",
        evidence_id="field-camera-rear-20260806",
    )

    assert source.is_available is True


def test_suer_security_source_stays_disabled_without_a_verified_uri():
    source = CameraSource(
        name="suer-security-pending",
        kind=CameraSourceKind.SUER_SECURITY,
        stream_uri=None,
        verified=False,
        verified_on=None,
    )

    assert source.is_available is False


def test_suer_security_source_cannot_be_marked_available_by_generic_asset_flag():
    with pytest.raises(ValueError, match="later adapter"):
        CameraSource(
            name="suer-security",
            kind=CameraSourceKind.SUER_SECURITY,
            stream_uri="rtsp://approved-later",
            verified=True,
            verified_on="2026-08-06",
            evidence_id="future-adapter-evidence",
        )


def test_verified_camera_rejects_blank_evidence_fields():
    with pytest.raises(ValueError, match="verified camera"):
        CameraSource(
            name="front-body",
            kind=CameraSourceKind.ROBOT_BODY,
            stream_uri=" ",
            verified=True,
            verified_on=" ",
            evidence_id=" ",
        )