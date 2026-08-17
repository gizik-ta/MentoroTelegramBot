import json

from features.common.models import TutorAd

from .base import BaseRepository


class AdRepository(BaseRepository):
    def _serialize_ad(self, user_ad: TutorAd) -> tuple:
        name = (
            json.dumps(user_ad.tutor_name) if user_ad.tutor_name is not None else None
        )
        photo = (
            json.dumps(user_ad.tutor_photo) if user_ad.tutor_photo is not None else None
        )
        return (
            user_ad.user_id,
            name,
            photo,
            user_ad.tutor_subject,
            user_ad.tutor_teaching_type,
            user_ad.tutor_experience,
            user_ad.tutor_classes_format,
            user_ad.tutor_description,
            user_ad.tutor_price,
            user_ad.finished,
            user_ad.tutor_username,
            user_ad.views,
            user_ad.likes,
            user_ad.state,
            getattr(user_ad, "is_bought", False),
            getattr(user_ad, "bought_time", None),
            getattr(user_ad, "publishing_end", None),
        )

    @staticmethod
    def row_to_ad(row) -> TutorAd:
        return TutorAd(
            ad_id=row["ad_id"],
            user_id=row["user_id"],
            tutor_name=json.loads(row["name"]) if row["name"] is not None else None,
            tutor_photo=json.loads(row["photo"]) if row["photo"] is not None else None,
            tutor_subject=row["subject"],
            tutor_teaching_type=row["teaching_type"],
            tutor_experience=row["experience"],
            tutor_classes_format=row["classes_format"],
            tutor_description=row["description"],
            tutor_price=row["price"],
            finished=bool(row["finished"]),
            tutor_username=row["tutor_username"],
            views=row["views"],
            likes=row["likes"],
            state=row["state"],
            is_bought=bool(row["is_bought"]),
            bought_time=row["bought_time"],
            publishing_end=row["publishing_end"],
        )

    async def add_ad(self, user_id: int, user_ad: TutorAd) -> int:
        user_ad.user_id = user_id
        values = self._serialize_ad(user_ad)
        cursor = await self.db.conn.execute(
            """
            INSERT INTO ads (
                user_id, name, photo, subject, teaching_type, experience,
                classes_format, description, price, finished, tutor_username,
                views, likes, state, is_bought, bought_time, publishing_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        new_id = cursor.lastrowid
        await self.db.conn.commit()
        return new_id

    async def update_ad(self, ad_id: int, user_id: int, user_ad: TutorAd) -> bool:
        user_ad.user_id = user_id
        values = self._serialize_ad(user_ad)[1:]  # Exclude user_id for SET block
        cursor = await self.db.conn.execute(
            """
            UPDATE ads SET
                name = ?, photo = ?, subject = ?, teaching_type = ?, experience = ?,
                classes_format = ?, description = ?, price = ?, finished = ?,
                tutor_username = ?, views = ?, likes = ?, state = ?,
                is_bought = ?, bought_time = ?, publishing_end = ?
            WHERE ad_id = ? AND user_id = ?
            """,
            (*values, ad_id, user_id),
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def get_by_id(self, ad_id: int) -> TutorAd | None:
        async with self.db.conn.execute(
            "SELECT * FROM ads WHERE ad_id = ?", (ad_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return self.row_to_ad(row) if row else None

    async def get_by_user_id(self, user_id: int) -> list[TutorAd]:
        async with self.db.conn.execute(
            "SELECT * FROM ads WHERE user_id = ? AND finished = 1 ORDER BY ad_id DESC",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self.row_to_ad(r) for r in rows]

    async def get_matched_ads(
        self, subject: str, current_filters: dict[str, str]
    ) -> list[TutorAd]:
        query = (
            "SELECT * FROM ads "
            "WHERE subject = ? "
            "AND finished = 1 "
            "AND state = 'published' "
            "AND is_bought = 1 "
            "AND (publishing_end IS NULL OR date(publishing_end) >= date('now'))"
        )
        params = [subject]

        price = current_filters.get("price")
        if price is not None:
            query += " AND price <= ?"
            params.append(int(price))

        teaching_type = current_filters.get("teaching_type")
        if teaching_type and teaching_type != "не уточнять":
            query += " AND (teaching_type = ? OR teaching_type = 'не уточнять')"
            params.append(teaching_type)

        classes_format = current_filters.get("classes_format")
        if classes_format:
            query += " AND (classes_format = ? OR classes_format = 'both')"
            params.append(classes_format)

        query += " ORDER BY ad_id DESC"

        async with self.db.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self.row_to_ad(r) for r in rows]

    async def get_liked_ads(self, user_id: int) -> list[TutorAd]:
        async with self.db.conn.execute(
            """
            SELECT a.* FROM ads a
            JOIN user_likes ul ON a.ad_id = ul.ad_id
            WHERE ul.user_id = ? AND a.finished = 1
            ORDER BY a.ad_id DESC
            """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [self.row_to_ad(r) for r in rows]

    async def delete_ad(self, ad_id: int, user_id: int) -> bool:
        cursor = await self.db.conn.execute(
            "DELETE FROM ads WHERE ad_id = ? AND user_id = ?", (ad_id, user_id)
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0

    async def like_ad(self, ad_id: int, user_id: int) -> None:
        async with self.db.conn.cursor() as cursor:
            await cursor.execute(
                "INSERT OR IGNORE INTO user_likes (user_id, ad_id) VALUES (?, ?)",
                (user_id, ad_id),
            )
            if cursor.rowcount > 0:
                await cursor.execute(
                    "UPDATE ads SET likes = likes + 1 WHERE ad_id = ?", (ad_id,)
                )
            await self.db.conn.commit()

    async def unlike_ad(self, ad_id: int, user_id: int) -> None:
        async with self.db.conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM user_likes WHERE user_id = ? AND ad_id = ?",
                (user_id, ad_id),
            )
            if cursor.rowcount > 0:
                await cursor.execute(
                    "UPDATE ads SET likes = MAX(0, likes - 1) WHERE ad_id = ?",
                    (ad_id,),
                )
            await self.db.conn.commit()

    async def is_liked(self, ad_id: int, user_id: int) -> bool:
        async with self.db.conn.execute(
            "SELECT 1 FROM user_likes WHERE user_id = ? AND ad_id = ?",
            (user_id, ad_id),
        ) as cursor:
            return (await cursor.fetchone()) is not None

    async def is_viewed(self, ad_id: int, user_id: int) -> bool:
        async with self.db.conn.execute(
            "SELECT 1 FROM user_views WHERE user_id = ? AND ad_id = ?",
            (user_id, ad_id),
        ) as cursor:
            return (await cursor.fetchone()) is not None

    async def is_bought(self, ad_id: int, user_id: int) -> bool:
        async with self.db.conn.execute(
            "SELECT is_bought FROM ads WHERE user_id = ? AND ad_id = ?",
            (user_id, ad_id),
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row["is_bought"]) if row else False

    async def view_ad(self, ad_id: int, user_id: int) -> None:
        async with self.db.conn.cursor() as cursor:
            await cursor.execute(
                "INSERT OR IGNORE INTO user_views (user_id, ad_id) VALUES (?, ?)",
                (user_id, ad_id),
            )
            await cursor.execute(
                "UPDATE ads SET views = views + 1 WHERE ad_id = ?",
                (ad_id,),
            )
            await self.db.conn.commit()

    async def update_state(self, ad_id: int, state: str) -> None:
        await self.db.conn.execute(
            "UPDATE ads SET state = ? WHERE ad_id = ?", (state, ad_id)
        )
        await self.db.conn.commit()

    async def set_ad_bought(
        self, user_id: int, ad_id: int | None, bought_str: str, end_str: str
    ) -> None:
        if ad_id is not None:
            await self.db.conn.execute(
                """
                UPDATE ads
                SET is_bought = TRUE,
                    bought_time = ?,
                    publishing_end = ?,
                    state = 'on_check'
                WHERE user_id = ? AND ad_id = ?
                """,
                (bought_str, end_str, user_id, ad_id),
            )
        else:
            await self.db.conn.execute(
                """
                UPDATE ads
                SET is_bought = TRUE,
                    bought_time = ?,
                    publishing_end = ?,
                    state = 'on_check'
                WHERE user_id = ?
                """,
                (bought_str, end_str, user_id),
            )
        await self.db.conn.commit()

    async def renew_ad(
        self,
        user_id: int,
        ad_id: int,
        bought_str: str,
        end_str: str,
    ) -> bool:
        cursor = await self.db.conn.execute(
            """
            UPDATE ads
            SET is_bought = TRUE,
                bought_time = ?,
                publishing_end = ?,
                state = 'published'
            WHERE user_id = ? AND ad_id = ?
            """,
            (bought_str, end_str, user_id, ad_id),
        )
        await self.db.conn.commit()
        return cursor.rowcount > 0
