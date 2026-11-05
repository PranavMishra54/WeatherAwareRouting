from math import hypot


def _distance_to_segment(point, start, end):
    x, y = point
    start_x, start_y = start
    end_x, end_y = end
    dx = end_x - start_x
    dy = end_y - start_y
    if dx == 0 and dy == 0:
        return hypot(x - start_x, y - start_y)

    fraction = max(
        0.0,
        min(1.0, ((x - start_x) * dx + (y - start_y) * dy) / (dx * dx + dy * dy)),
    )
    projection = (start_x + fraction * dx, start_y + fraction * dy)
    return hypot(x - projection[0], y - projection[1])


def _rdp(path, epsilon):
    if len(path) <= 2:
        return list(path)

    keep = {0, len(path) - 1}
    stack = [(0, len(path) - 1)]
    while stack:
        start_index, end_index = stack.pop()
        start = path[start_index]
        end = path[end_index]
        greatest_distance = epsilon
        greatest_index = None
        for index in range(start_index + 1, end_index):
            distance = _distance_to_segment(path[index], start, end)
            if distance > greatest_distance:
                greatest_distance = distance
                greatest_index = index
        if greatest_index is not None:
            keep.add(greatest_index)
            stack.append((start_index, greatest_index))
            stack.append((greatest_index, end_index))
    return [point for index, point in enumerate(path) if index in keep]


def simplify_path(path, max_points=600):
    path = list(path)
    if len(path) <= max_points:
        return path
    if max_points < 2:
        raise ValueError("max_points must be at least 2")

    epsilon = 0.002
    while True:
        simplified = _rdp(path, epsilon)
        if len(simplified) <= max_points:
            return simplified
        epsilon *= 2
