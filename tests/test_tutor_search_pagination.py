import asyncio

from features.tutor_searching.services.feed_service import FeedService
from features.tutor_searching.texts import TutorSearchingTexts


class FakeState:
    def __init__(self, data):
        self.data = data

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **values):
        self.data.update(values)


def test_ad_position_is_rendered_as_one_based_current_over_total():
    assert TutorSearchingTexts.ad_position(2, 29) == "<b>3/29</b>\n\n"


def test_pagination_rejects_stale_callbacks_and_stays_in_bounds():
    async def scenario():
        state = FakeState({"cached_ad_ids": [11, 12, 13], "current_ad_index": 1})

        stale = await FeedService.shift_page(state, "next", expected_index=0)
        moved = await FeedService.shift_page(state, "next", expected_index=1)
        beyond_end = await FeedService.shift_page(state, "next", expected_index=2)
        return state.data, stale, moved, beyond_end

    data, stale, moved, beyond_end = asyncio.run(scenario())

    assert stale is False
    assert moved is True
    assert beyond_end is False
    assert data["current_ad_index"] == 2
