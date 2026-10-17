import struct,sys
f=open(sys.argv[1],'rb')
def r(fmt):return struct.unpack('<'+fmt,f.read(struct.calcsize('<'+fmt)))[0]
def s():n=r('Q');return f.read(n).decode('utf-8','replace')
assert f.read(4)==b'GGUF';v=r('I');nt=r('Q');nk=r('Q')
T={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
def val(t):
    if t==8:return s()
    if t==9:
        at=r('I');n=r('Q');a=[val(at) for _ in range(n)];return a
    return r(T[t])
print('version',v,'tensors',nt)
for _ in range(nk):
    k=s();t=r('I');x=val(t)
    if isinstance(x,list):x=f'[list len={len(x)}] '+str(x[:8])
    if isinstance(x,str) and len(x)>300:x=x[:300]+'...'
    print(k,'=',x)
