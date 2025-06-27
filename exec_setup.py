import cx_Freeze

cx_Freeze.setup(
    name="fitsync",
    version="0.1",
    description="FitSync - A multi-platform fitness data synchronization tool supporting Strava, Garmin Connect, OneDrive, IGPSport and Intervals.icu.",
    executables=[cx_Freeze.Executable("src/main.py")],
)
