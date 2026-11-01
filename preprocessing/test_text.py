"""Kiểm thử tiền xử lý: python -m unittest preprocessing.test_text"""
import unittest

from preprocessing.text import clean_text, detect_lang, emoji_tags, extract_hashtags, mask_pii


class CleanTextTest(unittest.TestCase):
    def test_teencode_and_lowercase(self):
        self.assertEqual(clean_text("Ko đc ĐÂU, mn ơi").text, "không được đâu, mọi người ơi")

    def test_tone_old_style(self):
        self.assertEqual(clean_text("hoà thuý quý").text, "hòa thúy quý")

    def test_repeated_chars_and_emoji(self):
        self.assertEqual(clean_text("đẹppppp quáaaa nhéee 😍😍😍").text, "đẹp quá nhé 😍")

    def test_real_words_untouched(self):
        words = "cứu hưu rượu khỏe mía quả gạo ngoài huệ khuya thuở bưởi xoong tươi"
        self.assertEqual(clean_text(words).text, words)

    def test_pii_masked(self):
        r = clean_text("Liên hệ 0912 345 678 hoặc a.b@gmail.com nha @nguyenvana")
        self.assertNotIn("0912", r.text)
        self.assertNotIn("gmail", r.text)
        self.assertNotIn("nguyenvana", r.text)
        self.assertEqual(r.pii_masked, 3)

    def test_spam(self):
        self.assertTrue(clean_text("Kiếm tiền online, inbox zalo 0987654321 nhé").is_spam)
        self.assertTrue(clean_text("👍👍").is_spam)  # không có chữ
        self.assertFalse(clean_text("Giá vàng tăng quá nhanh, lo thật").is_spam)

    def test_lang(self):
        self.assertEqual(detect_lang("giá vàng hôm nay tăng mạnh"), "vi")
        self.assertEqual(detect_lang("gia vang hom nay khong tang"), "vi")
        self.assertEqual(detect_lang("this video is amazing"), "other")
        self.assertEqual(detect_lang("ok"), "unk")

    def test_url_removed(self):
        self.assertEqual(clean_text("xem ở https://abc.vn/x?y=1 nhé").text, "xem ở nhé")

    def test_emoji_tags(self):
        self.assertIn("emovui", emoji_tags("hay quá 😂"))
        self.assertIn("emogian", emoji_tags("bực 😡"))

    def test_hashtags(self):
        self.assertEqual(extract_hashtags("Giá vàng #GiáVàng tăng #gia_vang #GiáVàng, mail a#b"), ["#giávàng", "#gia_vang"])

    def test_mask_pii_counts(self):
        self.assertEqual(mask_pii("gọi +84 912345678")[1], 1)


if __name__ == "__main__":
    unittest.main()
