## Makefile

TARGET		= galasm
OBJS		= galasm.o support.o jedec.o localize.o

CFLAGS		= -Wall -O2 -Iinclude -I.


all: $(TARGET)

$(TARGET): $(OBJS)
	gcc -o $@ $(OBJS)

clean:
	-rm $(OBJS)
	-rm -f *.[oa] $(TARGET) Makefile.bak

cleantilde:
	/usr/bin/find . -regex ".+~$$" -exec /bin/rm {} \;
 
