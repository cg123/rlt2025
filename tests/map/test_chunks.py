"""Tests for chunk coordinate conversion, especially negative coordinates."""

import pytest

from rlt2025.map.chunks import CHUNK_DEPTH, CHUNK_SIZE, chunk_to_world, world_to_chunk


class TestChunkCoordinates:
    """Test chunk coordinate conversion functions."""

    @pytest.mark.parametrize(
        "world_x,world_y,expected_cx,expected_cy,expected_lx,expected_ly",
        [
            (0, 0, 0, 0, 0, 0),  # Origin
            (31, 31, 0, 0, 31, 31),  # Edge of first chunk
            (32, 32, 1, 1, 0, 0),  # Start of second chunk
            (-1, -1, -1, -1, 31, 31),  # Just into negative
            (-32, -32, -1, -1, 0, 0),  # Edge case
            (-33, -33, -2, -2, 31, 31),  # Further negative
            (15, -15, 0, -1, 15, 17),  # Mixed signs
            (-15, 15, -1, 0, 17, 15),  # Mixed signs reversed
        ],
    )
    def test_world_to_chunk_conversion(
        self, world_x, world_y, expected_cx, expected_cy, expected_lx, expected_ly
    ):
        """Test world_to_chunk function with various coordinates including negatives."""
        chunk_key, (lx, ly, lz) = world_to_chunk(world_x, world_y, 0)

        # Verify chunk coordinates
        assert chunk_key.cx == expected_cx, (
            f"Expected chunk X {expected_cx}, got {chunk_key.cx}"
        )
        assert chunk_key.cy == expected_cy, (
            f"Expected chunk Y {expected_cy}, got {chunk_key.cy}"
        )

        # Verify local coordinates
        assert lx == expected_lx, f"Expected local X {expected_lx}, got {lx}"
        assert ly == expected_ly, f"Expected local Y {expected_ly}, got {ly}"
        assert lz == 0, f"Expected local Z 0, got {lz}"

    @pytest.mark.parametrize(
        "world_x,world_y",
        [
            (0, 0),
            (31, 31),
            (32, 32),
            (-1, -1),
            (-32, -32),
            (-33, -33),
            (15, -15),
            (-15, 15),
            (100, -200),
            (-500, 300),
        ],
    )
    def test_round_trip_conversion(self, world_x, world_y):
        """Test that world -> chunk -> world conversion is exact."""
        # Convert world coordinates to chunk coordinates
        chunk_key, (lx, ly, lz) = world_to_chunk(world_x, world_y, 0)

        # Convert back to world coordinates
        world_pos = chunk_to_world(chunk_key, lx, ly, lz)

        # Verify round-trip conversion is exact
        assert world_pos.x == world_x, (
            f"Round-trip X failed: {world_x} -> {world_pos.x}"
        )
        assert world_pos.y == world_y, (
            f"Round-trip Y failed: {world_y} -> {world_pos.y}"
        )
        assert world_pos.z == 0, f"Round-trip Z failed: 0 -> {world_pos.z}"

    def test_local_coordinates_in_bounds(self):
        """Test that local coordinates are always within chunk bounds."""
        test_coordinates = [
            (0, 0),
            (-1, -1),
            (31, 31),
            (32, 32),
            (-32, -32),
            (-33, -33),
            (100, 200),
            (-100, -200),
            (567, -234),
        ]

        for world_x, world_y in test_coordinates:
            chunk_key, (lx, ly, lz) = world_to_chunk(world_x, world_y, 0)

            assert 0 <= lx < CHUNK_SIZE, (
                f"Local X {lx} out of bounds for world ({world_x}, {world_y})"
            )
            assert 0 <= ly < CHUNK_SIZE, (
                f"Local Y {ly} out of bounds for world ({world_x}, {world_y})"
            )
            assert 0 <= lz < CHUNK_DEPTH, (
                f"Local Z {lz} out of bounds for world ({world_x}, {world_y})"
            )
