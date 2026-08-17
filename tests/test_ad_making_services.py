from features.ad_making.services import AdMakingServices
from features.common.models import TutorAd


def test_prepare_updated_ad_sends_rejected_ad_back_to_moderation():
    ad = TutorAd(state="rejected", is_bought=False)

    prepared = AdMakingServices.prepare_updated_ad(ad)

    assert prepared.state == "on_check"


def test_prepare_updated_ad_keeps_unpaid_ad_waiting_for_payment():
    ad = TutorAd(state="payment_waiting", is_bought=False)

    prepared = AdMakingServices.prepare_updated_ad(ad)

    assert prepared.state == "payment_waiting"
