


def get_path_distance_km(points):
    distance = 0
    previous_point = None
    for point in points:
        if previous_point is not None:
            distance += previous_point.distance(point) * 100
        previous_point = point

    return round(distance, 2)