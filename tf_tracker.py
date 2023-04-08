from telegram.ext import ContextTypes
from l18n import LK_TF_STATUS, l18n


class TerraformingTracker:
    MAX_OCEANS = 9
    MAX_OXYGEN = 14
    MIN_TEMP = -30
    MAX_TEMP = 8

    def __init__(self):
        self.last = 0

    def get_total(self, oceans, oxygen, temp) -> int:
        """ percentage """
        return round(
            (oceans / self.MAX_OCEANS
             + oxygen / self.MAX_OXYGEN
             + (temp - self.MIN_TEMP) / (self.MAX_TEMP - self.MIN_TEMP)) / 3 * 100
        )

    def check(self, reply: dict):
        game = reply['game']
        oceans = game['oceans']
        assert 0 <= oceans <= self.MAX_OCEANS
        oxygen = game['oxygenLevel']
        assert 0 <= oxygen <= self.MAX_OXYGEN
        temp = game['temperature']
        assert self.MIN_TEMP <= temp <= self.MAX_TEMP
        current_total = self.get_total(oceans, oxygen, temp)
        if current_total // 10 > self.last // 10:
            self.last = current_total
            return oceans, oxygen, temp
        else:
            return False

    def make_message(self, context: ContextTypes.DEFAULT_TYPE, oceans, oxygen, temp):
        return l18n(context, LK_TF_STATUS) \
            .format(self.last, oceans, oxygen, temp)
