#include <gtest/gtest.h>

#include "ai_robot_cpp_example/status_formatter.hpp"

TEST(StatusFormatter, PrefixesTheState)
{
  EXPECT_EQ(ai_robot_cpp_example::status_line("ready"), "ai_robot_cpp_example:ready");
}
