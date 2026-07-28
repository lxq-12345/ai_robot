#ifndef AI_ROBOT_CPP_EXAMPLE__STATUS_FORMATTER_HPP_
#define AI_ROBOT_CPP_EXAMPLE__STATUS_FORMATTER_HPP_

#include <string>

namespace ai_robot_cpp_example
{

inline std::string status_line(const std::string & state)
{
  return "ai_robot_cpp_example:" + state;
}

}  // namespace ai_robot_cpp_example

#endif  // AI_ROBOT_CPP_EXAMPLE__STATUS_FORMATTER_HPP_
