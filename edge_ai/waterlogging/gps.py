class SimulatedGPS:

    def __init__(self):
        self.latitude = 13.0358
        self.longitude = 77.5970

    def get_location(self, frame_number):

        latitude = self.latitude + (frame_number * 0.000001)
        longitude = self.longitude + (frame_number * 0.000001)

        return {
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6)
        }


if __name__ == "__main__":

    gps = SimulatedGPS()

    print("Simulated GPS loaded successfully.")

    for frame in [0, 100, 500, 900]:

        location = gps.get_location(frame)

        print(
            "Frame:",
            frame,
            "Latitude:",
            location["latitude"],
            "Longitude:",
            location["longitude"]
        )