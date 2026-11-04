CXX ?= g++
CXXFLAGS ?= -std=c++11 -O2 -Wall -Wextra
VIVEHUB_DIR ?= ../../VIVEHub-Linux

vut_capture: vut_capture.cpp
	$(CXX) $(CXXFLAGS) -I$(VIVEHUB_DIR)/sdk/include -o $@ $< $(VIVEHUB_DIR)/sdk/lib/libvut_sdk.a -lpthread

clean:
	rm -f vut_capture
