:cmake_minimum_required(VERSION 3.10)
project(MusicWidgetCpp CXX)

# C++ 표준 설정
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED TRUE)

# GTKmm 3 의존성 찾기
find_package(PkgConfig REQUIRED)
pkg_check_modules(GTKMM REQUIRED gtkmm-3.0)

# DBus 의존성 찾기
pkg_check_modules(DBUS REQUIRED dbus-1)
# 또는 gio-2.0 (GLib/GIO DBus 래퍼 사용 시)
pkg_check_modules(GIO REQUIRED gio-2.0)


# 소스 파일 정의
set(SOURCE_FILES
    src/main.cpp
    src/MusicWidget.cpp
)

# 헤더 파일 디렉토리 포함
include_directories(src ${GTKMM_INCLUDE_DIRS} ${DBUS_INCLUDE_DIRS} ${GIO_INCLUDE_DIRS})

# 실행 파일 생성
add_executable(${PROJECT_NAME} ${SOURCE_FILES})

# 라이브러리 연결
target_link_libraries(${PROJECT_NAME}
    ${GTKMM_LIBRARIES}
    ${DBUS_LIBRARIES}
    ${GIO_LIBRARIES}
)

# (선택 사항) style.css를 빌드 디렉토리로 복사
install(FILES style.css DESTINATION ${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME})
