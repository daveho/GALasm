## Makefile

TARGET		= galasm
OBJS		= galasm.o support.o jedec.o localize.o
CC          = gcc

CFLAGS		= -Wall -O2
LDFLAGS		=
PYTHON		?= python3


all: $(TARGET)

$(TARGET): $(OBJS)
	gcc $(LDFLAGS) -o $@ $(OBJS)

check: $(TARGET)
	$(PYTHON) ../tests/run_tests.py --galasm ./$(TARGET)

clean:
	-rm $(OBJS)
	-rm -f *.[oa] $(TARGET) Makefile.bak

cleantilde:
	/usr/bin/find . -regex ".+~$$" -exec /bin/rm {} \;
 
