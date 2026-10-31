#import <AppKit/AppKit.h>
#import <QuartzCore/QuartzCore.h>
#include <sys/sysctl.h>
#include <stdint.h>
static uint64_t counter(void){uint64_t v=0;size_t n=sizeof v;sysctlbyname("debug.nvaccel_iop_ok_h4",&v,&n,NULL,0);return v;}
static const char *metrics[]={"entry","fence","ready","copy","total"};
static uint64_t metric(unsigned i,const char *field){char key[100];snprintf(key,sizeof key,"debug.nvaccel_perf_%s_%s",metrics[i],field);uint64_t v=0;size_t n=sizeof v;sysctlbyname(key,&v,&n,NULL,0);return v;}
@interface AnimationProbe:NSObject { @public uint64_t startNS[5],startCount[5]; }
@property NSWindow *window;
@property NSArray<NSWindow*> *windows;
@property double duration;
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
 if(now-self.started>=self.duration){
  double seconds=now-self.started;
  printf("ANIMATION COMPLETE seconds=%.6f callback_rate=%.2f panel_copies_per_second=%.2f callbacks=%llu configured_link_duration_ms=%.4f\n",seconds,self.ticks/seconds,(counter()-self.copies)/seconds,self.ticks,link.duration*1000);fflush(stdout);
  for(unsigned i=0;i<5;i++){uint64_t count=metric(i,"count")-startCount[i],ns=metric(i,"ns")-startNS[i];printf("%s n=%llu mean_ms=%.4f\n",metrics[i],count,count?ns/(double)count/1e6:0);}fflush(stdout);
  [self.link invalidate];for(NSWindow*w in self.windows)[w orderOut:nil];[NSApp terminate:nil];
 }
}
@end
int main(void){@autoreleasepool{
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];[NSApp finishLaunching];
 AnimationProbe *p=[AnimationProbe new];setenv("G6MF_SERVER_ANIMATION","1",1);
 p.duration=getenv("G6MF_PRESSURE_SECONDS")?MAX(2,MIN(12,atof(getenv("G6MF_PRESSURE_SECONDS")))):8;
 NSMutableArray *windows=[NSMutableArray new];NSRect visible=NSScreen.mainScreen.visibleFrame;
 double width=MAX(120,(visible.size.width-48)/4),height=MAX(100,(visible.size.height-120)/3);
 for(unsigned index=0;index<12;index++){

 p.window=[[NSPanel alloc]initWithContentRect:NSMakeRect(visible.origin.x+12+(index%4)*width,visible.origin.y+20+(index/4)*(height+22),width-6,height-6) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskNonactivatingPanel backing:NSBackingStoreBuffered defer:NO];
 p.window.title=[NSString stringWithFormat:@"G6MF cache %u — auto close",index+1];p.window.releasedWhenClosed=NO;p.window.opaque=YES;
 p.window.backgroundColor=[NSColor colorWithCalibratedHue:index/12.0 saturation:0.4 brightness:0.3 alpha:1];
 p.window.contentView.wantsLayer=YES;
 CALayer *bar=[CALayer layer];bar.bounds=CGRectMake(0,0,width/3,height/2);bar.position=CGPointMake(width/2,height/2);bar.cornerRadius=16;
 bar.backgroundColor=[NSColor colorWithCalibratedHue:(index+3)/12.0 saturation:0.7 brightness:0.9 alpha:1].CGColor;
 [p.window.contentView.layer addSublayer:bar];
 CABasicAnimation *a=[CABasicAnimation animationWithKeyPath:@"position.x"];a.fromValue=@(width/5);a.toValue=@(width*4/5);a.duration=0.7+index*0.03;a.autoreverses=YES;a.repeatCount=HUGE_VALF;[bar addAnimation:a forKey:@"move"];
 [windows addObject:p.window];[p.window orderFrontRegardless];
 }
 p.windows=windows;p.window=windows[0];p.launched=CACurrentMediaTime();
 p.link=[p.window.contentView displayLinkWithTarget:p selector:@selector(tick:)];p.link.preferredFrameRateRange=CAFrameRateRangeMake(30,165,165);[p.link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
 [NSTimer scheduledTimerWithTimeInterval:20 repeats:NO block:^(NSTimer *timer){fprintf(stderr,"ANIMATION TIMEOUT\n");[p.link invalidate];for(NSWindow*w in p.windows)[w orderOut:nil];[NSApp terminate:nil];}];
 [NSApp run];return 0;
}}
