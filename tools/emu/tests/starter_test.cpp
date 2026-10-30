// First boot: pick a village, then -- where it has more than one -- the Genin
// to start with. Konoha offers NARUTO, SASUKE and SAKURA; Kiri has only HAKU,
// so tapping Kiri finishes the first boot at once. The mixed pool (ALL) picks
// at random.
#include "Arduino.h"
#include "Arduino_GFX_Library.h"
#include "Preferences.h"
#include "pet.h"
#include "party.h"
#include <cstdio>
#include <cstring>
uint32_t g_seed=29; FakeSerial Serial; FakeESP ESP; FakeWire Wire;
volatile int g_touchX=0,g_touchY=0; volatile bool g_touchDown=false;
int FakeSerial::available(){return 0;} String FakeSerial::readStringUntil(char){return String("");}
void FakeESP::restart(){exit(0);}

void setup(); void render(); void onTap(int16_t x, int16_t y);
int16_t starterOf(uint8_t region, uint8_t i);
uint8_t starterCountShown(uint8_t region);
extern Pet pet;
extern bool starterRegionDone;   // a WIPE reboots on a board; here we reset it by hand

static int bad=0;
static void ck(bool ok,const char*w){printf("%s  %s\n",ok?"PASS":"FAIL",w); if(!ok)bad++;}

// where renderRegionPick draws row i, and where renderStarterSelect draws row i
static int regionRowY(int i){ return 108 + i*72 + 30; }
int uiStarterRowCenterY(int i);
#define STARTER_Y(i) uiStarterRowCenterY(i)

int main(){
  setup();
  render();
  ck(pet.awaitingStarter(), "a brand new save asks for a starter");

  // --- each village's starters, pinned
  const int16_t want0[4] = { 1, 17, 21, 24 };
  const uint8_t wantN[4] = { 3, 3, 1, 3 };
  for (uint8_t r = 0; r < 4; r++) {
    char m[64]; snprintf(m,sizeof(m),"%s starts with its own Genin", REGIONS[r].name);
    ck(REGIONS[r].starterCount == wantN[r] && REGIONS[r].starters[0] == want0[r] && regionHatchable(r), m);
  }
  ck(REGIONS[REGION_ALL].starterCount == 10, "the mixed pool holds all ten");

  // --- Kiri: one starter, so the tap on the village is the whole first boot
  onTap(233, regionRowY(2));                  // KIRI
  ck(pet.region == 2, "tapping a village on the first screen sets the scroll village");
  ck(!pet.awaitingStarter(), "and its single Genin is chosen without a second screen");
  ck(pet.eggPeek() == 21, "the waiting scroll is HAKU's");
  // --- and it survives a reload: village is persisted, the flow is not repeated
  {
    Pet again; again.begin();
    ck(again.region == 2, "the village choice is saved");
    ck(!again.awaitingStarter(), "and the first boot does not run a second time");
  }

  // --- Konoha: three to choose from, so a second screen asks
  {
    pet.factoryReset();
    pet.begin();
    ck(pet.awaitingStarter(), "a wiped save asks again");
    starterRegionDone = false;
    render();
    onTap(233, regionRowY(0));                // KONOHA
    ck(pet.region == 0 && pet.awaitingStarter(), "Konoha goes on to the Genin choice");
    ck(starterCountShown(0) == 3, "which offers all three of Team 7");
    render();
    onTap(233, STARTER_Y(1));                 // the second row: SASUKE
    ck(!pet.awaitingStarter() && pet.eggPeek() == 2, "and tapping SASUKE makes him the first scroll");
  }

  printf("%s\n", bad?"FAILURES":"all good");
  return bad?1:0;
}
