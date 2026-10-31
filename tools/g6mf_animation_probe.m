#import <AppKit/AppKit.h>
#import <QuartzCore/QuartzCore.h>
#include <sys/sysctl.h>
#include <stdint.h>
static uint64_t counter(void){uint64_t v=0;size_t n=sizeof v;sysctlbyname("debug.nvaccel_iop_ok_h4",&v,&n,NULL,0);return v;}
static const char *metrics[]={"entry","fence","ready","copy","total"};
static uint64_t metric(unsigned i,const char *field){char key[100];snprintf(key,sizeof key,"debug.nvaccel_perf_%s_%s",metrics[i],field);uint64_t v=0;size_t n=sizeof v;sysctlbyname(key,&v,&n,NULL,0);return v;}
@interface AnimationProbe:NSObject { @public uint64_t startNS[5],startCount[5]; }
@property NSWindow *window;
@property CALayer *bar;
@property CADisplayLink *link;
@property double launched,started;
@property uint64_t copies,ticks;
@end
@implementation AnimationProbe
-(void)tick:(CADisplayLink*)link {
 double now=CACurrentMediaTime(),elapsed=now-self.launched;
 if(!getenv("G6MF_SERVER_ANIMATION")){
  [CATransaction begin];[CATransaction setDisableActions:YES];
  self.bar.position=CGPointMake(450+310*sin(elapsed*4),260+160*cos(elapsed*3));
  [CATransaction commit];
 }
 if(elapsed<2)return;
 if(!self.started){self.started=now;self.copies=counter();self.ticks=0;for(unsigned i=0;i<5;i++){startNS[i]=metric(i,"ns");startCount[i]=metric(i,"count");}}
 self.ticks++;
 if(now-self.started>=12){
  double seconds=now-self.started;
  printf("ANIMATION COMPLETE seconds=%.6f callback_rate=%.2f panel_copies_per_second=%.2f callbacks=%llu configured_link_duration_ms=%.4f\n",seconds,self.ticks/seconds,(counter()-self.copies)/seconds,self.ticks,link.duration*1000);fflush(stdout);
  for(unsigned i=0;i<5;i++){uint64_t count=metric(i,"count")-startCount[i],ns=metric(i,"ns")-startNS[i];printf("%s n=%llu mean_ms=%.4f\n",metrics[i],count,count?ns/(double)count/1e6:0);}fflush(stdout);
  [self.link invalidate];[self.window orderOut:nil];[NSApp terminate:nil];
 }
}
@end
int main(void){@autoreleasepool{
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];[NSApp finishLaunching];
 AnimationProbe *p=[AnimationProbe new];
 p.window=[[NSPanel alloc]initWithContentRect:NSMakeRect(100,140,900,520) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskNonactivatingPanel backing:NSBackingStoreBuffered defer:NO];
 p.window.title=@"G6MF animation probe — closes automatically";p.window.releasedWhenClosed=NO;p.window.opaque=YES;p.window.backgroundColor=NSColor.blackColor;
 p.window.contentView.wantsLayer=YES;p.window.contentView.layer.backgroundColor=NSColor.blackColor.CGColor;
 p.bar=[CALayer layer];p.bar.bounds=CGRectMake(0,0,180,180);p.bar.backgroundColor=NSColor.systemOrangeColor.CGColor;p.bar.cornerRadius=24;[p.window.contentView.layer addSublayer:p.bar];
 if(getenv("G6MF_SERVER_ANIMATION")){p.bar.position=CGPointMake(450,260);CABasicAnimation *a=[CABasicAnimation animationWithKeyPath:@"position.x"];a.fromValue=@140;a.toValue=@760;a.duration=0.8;a.autoreverses=YES;a.repeatCount=HUGE_VALF;[p.bar addAnimation:a forKey:@"test"];}
 [p.window orderFrontRegardless];p.launched=CACurrentMediaTime();
 p.link=[p.window.contentView displayLinkWithTarget:p selector:@selector(tick:)];p.link.preferredFrameRateRange=CAFrameRateRangeMake(30,165,165);[p.link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
 [NSTimer scheduledTimerWithTimeInterval:20 repeats:NO block:^(NSTimer *timer){fprintf(stderr,"ANIMATION TIMEOUT\n");[p.link invalidate];[p.window orderOut:nil];[NSApp terminate:nil];}];
 [NSApp run];return 0;
}}
