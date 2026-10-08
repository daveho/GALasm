## Makefile

TARGET		= galasm
OBJS		= galasm.o support.o jedec.o localize.o
CC          = gcc

CFLAGS		= -Wall -O2
LDFLAGS		=
PYTHON		?= python3

# Architectures to build for, e.g. ARCHS="x86_64 arm64" for a macOS
# universal binary.  Empty builds for the compiler's default architecture.
ARCHS		=
TARGET_ARCH	= $(addprefix -arch ,$(ARCHS))

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) $(TARGET_ARCH) -o $@ $(OBJS)

check: $(TARGET)
	$(PYTHON) ../tests/run_tests.py --galasm ./$(TARGET)

clean:
	-rm -f $(OBJS) *.[oa] $(TARGET) Makefile.bak

cleantilde:
	/usr/bin/find . -regex ".+~$$" -exec /bin/rm {} \;
 
