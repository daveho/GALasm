## Makefile

TARGET		= galasm
OBJS		= galasm.o support.o jedec.o localize.o

CFLAGS		= -Wall -O2
CPPFLAGS	= -Iinclude -I.
LDFLAGS		=


all: $(TARGET)

$(TARGET): $(OBJS)
	gcc $(LDFLAGS) -o $@ $(OBJS)

clean:
	-rm $(OBJS)
	-rm -f *.[oa] $(TARGET) Makefile.bak

cleantilde:
	/usr/bin/find . -regex ".+~$$" -exec /bin/rm {} \;
 
