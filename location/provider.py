class CoordinatesProvider:
    def __init__(self, fake_data=None):
        self.fake_data = fake_data

    def get_coordinates(self):
        if not self.fake_data:
            return self.fake_data.pop()
        else:
            return self._get_adb_location()

    def _get_adb_location(self):

        pass
