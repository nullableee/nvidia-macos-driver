#include <cpuid.h>
#include <pthread.h>
#include <sys/qos.h>
#include <time.h>
#include <stdio.h>
#include <stdint.h>
static unsigned coretype(void){unsigned a,b,c,d;__cpuid_count(0x1a,0,a,b,c,d);return a>>24;}
static unsigned apic(void){unsigned a,b,c,d;__cpuid_count(1,0,a,b,c,d);return b>>24;}
int main(void){
 for(unsigned qos=0;qos<2;qos++){
  pthread_set_qos_class_self_np(qos?QOS_CLASS_USER_INTERACTIVE:QOS_CLASS_DEFAULT,0);
  for(unsigned trial=0;trial<12;trial++){
   unsigned ct=coretype(),id=apic();uint64_t start=clock_gettime_nsec_np(CLOCK_UPTIME_RAW),cpu=clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID);
   volatile uint64_t v=17;
   for(unsigned i=0;i<3000000;i++)v=(v*6364136223846793005ull+1)^((v>>17)+i);
   uint64_t cpuNS=clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)-cpu,wall=clock_gettime_nsec_np(CLOCK_UPTIME_RAW)-start;
   printf("qos=%s type=%02x->%02x apic=%u->%u cpu_ms=%.3f wall_ms=%.3f value=%llu\n",qos?"UI":"default",ct,coretype(),id,apic(),cpuNS/1e6,wall/1e6,v);
  }
 }
}
