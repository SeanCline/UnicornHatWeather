#include <vector>
#include <deque>
#include <array>
#include <string>
#include <random>
#include <cstdint>
#include "gif.h" //< https://github.com/charlietangora/gif-h


namespace {
	template <typename IntT>
	static IntT randint(IntT low, IntT high) {
		thread_local static std::mt19937 gen(std::random_device{}());
		std::uniform_int_distribution<IntT> distrib(low, high);
		return distrib(gen);
	}
}

struct Anim {
	constexpr static auto colorCycle = std::array{ 150, 150, 200, 200, 90, 90, 60, 90};

	Anim(int width, int height, std::string filename, int frameDelay = 15)
		: w_(width), h_(height), delay_(frameDelay)
	{
		GifBegin(&g_, filename.c_str(), w_, h_, delay_);
	}

	~Anim() {
		GifEnd(&g_);
	}

	// Update to the next state. Returns false when the animation is done.
	bool tick() {
		if (frameNum_ > 200)
			return false;

		++frameNum_;

		auto canMove = [](const auto& rows, size_t rowNum, int distance, int width) {
			const auto& row = rows[rowNum];
			const auto newOffset = row.offset + distance;

			// Check the edge.
			const auto newLeft = row.left(width) + distance;
			if (newLeft < 0)
				return false;

			const auto newRight = row.right(width) + distance;
			if (newRight >= width)
				return false;

			// Check the row above.
			if (rowNum != 0) {
				const auto differenceWithAbove = (rows.at(rowNum - 1).offset - newOffset);
				if (differenceWithAbove > 1 || differenceWithAbove < -1)
					return false;
			}

			// Check the row below.
			if (rowNum < (rows.size()-1)) {
				const auto differenceWithBelow = (rows.at(rowNum + 1).offset - newOffset);
				if (differenceWithBelow > 1 || differenceWithBelow < -1)
					return false;
			}

			return true;
		};

		// Try to move a row in a random direction.
		for (size_t rowNum = 0; rowNum < rows_.size(); ++rowNum) {
			const auto distance = randint(-1, 1);
			if (distance == 0)
				continue;

			if (canMove(rows_, rowNum, distance, w_)) {
				rows_.at(rowNum).offset += distance;
				break;
			}
		}

		return true;
	}

	// Writes the frame to the file.
	void writeFrame() {
		auto frame = buildFrame();

		auto frameData = std::vector<uint8_t>();
		frameData.reserve(frame.size() * 4);
		for (Color c : frame)
		{
			frameData.push_back(c.r);
			frameData.push_back(c.g);
			frameData.push_back(c.b);
			frameData.push_back(c.a);
		}

		GifWriteFrame(&g_, frameData.data(), w_, h_, delay_);
	}

private: // Internal functions.

	struct Color {
		uint8_t r = 0, g = 0, b = 0, a = 0;
	};

	std::vector<Color> buildFrame() {
		std::vector<Color> frame(w_ * h_);

		// Create the spinning effect by cycling through which color we start on.
		size_t colorIndex = frameNum_ % colorCycle.size();
		for (size_t rowIndex = 0; rowIndex < rows_.size(); ++rowIndex) {
			const auto& row = rows_.at(rowIndex);
			for (auto i = row.left(w_); i < row.right(w_); ++i) {
				colorIndex = (colorIndex + 1) % colorCycle.size();
				const auto brightness = static_cast<uint8_t>(colorCycle[colorIndex]);
				frame.at(rowIndex * w_ + i) = {brightness, brightness, brightness };
			}
		}

		return frame;
	}

private: // Data.
	int w_ = 0, h_ = 0;
	int delay_ = 0;
	GifWriter g_ = {0};
	unsigned long frameNum_ = 0;

private: // Animation specific data.
	struct Row {
		int8_t length, offset;

		int midpoint(int width) const {
			return width / 2 + offset;
		}

		int left(int width) const {
			return midpoint(width) - (length / 2);
		}

		int right(int width) const {
			return left(width) + length;
		}
	};

	std::vector<Row> rows_ = {
		{6}, {6}, {5}, {5}, {4}, {3}, {2}, {1}
	};
};


int main() {
	Anim a(8, 8, "tornado.gif");

	while (a.tick())
		a.writeFrame();
}