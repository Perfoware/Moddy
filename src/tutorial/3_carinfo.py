'''
Created on 12.02.2017

@author: Klaus Popp

Simulate the behavior of a (extremely simplified) car infotainment system.

The main state is simulated with a Moddy Finite state machine. (Off, Booting, NormalOp etc).
The normal state has several nested sub-state machines, such as 
 'Apps' (Radio, Navi) - jumps between the different applications (in this simulation, the apps have no function)
 'Volume' - manages the audio volume

The Stim part simulates user events.

'''

from moddy import *
whiteOnGreen = {'boxStrokeColor':'black', 'boxFillColor':'green', 'textColor':'white'}
whiteOnRed = {'boxStrokeColor':'black', 'boxFillColor':'red', 'textColor':'white'}
whiteOnBlue = {'boxStrokeColor':'blue', 'boxFillColor':'blue', 'textColor':'white'}
blackOnWhite = {'boxStrokeColor':'black', 'boxFillColor':'white', 'textColor':'black'}

class CarInfoSystem(simFsmPart):

    def __init__(self, sim, objName):
        statusBoxReprMap = {
            'Off':      (None, blackOnWhite),
            'Standby':  ('SBY', whiteOnRed),
            'Booting':  ('BOOT', whiteOnBlue),
            'NormalOp': ('NORM', whiteOnGreen),
            'Shutdown':  ('SD', whiteOnRed)
        }
        
        
        super().__init__(sim=sim, objName=objName, fsm=self.FSM(), statusBoxReprMap=statusBoxReprMap)

        # Ports & Timers
        self.createPorts('in', ['powerPort', 'ignitionPort', 'buttonPort'])
        self.createPorts('out', ['audioPort', 'visualPort'])
        self.createTimers(['bootTmr', 'shutdownTmr', 'clockTmr'])

        
    class FSM(Fsm):
        def __init__(self):
            
            transitions = { 
                '': # FSM uninitialized
                    [('INITIAL', 'Off')],                
                'Off': 
                    [('PowerApplied', 'Standby')],
                'Standby':
                    # This transition is triggered whenever ANY message arrives on the powerButtonPort
                    [('PowerButton', 'Booting'),
                     ('IgnitionOn', 'Booting')],
                'Booting':
                    [('bootTmr_Expired', 'NormalOp')],
                'NormalOp':
                     # The following two lines specify nested state machines, executing in parallel
                    [('Apps' , CarInfoSystem.FSM.ApplicationsFsm ),  
                     ('Vol' , CarInfoSystem.FSM.VolumeFsm ),         
                     # This transition is triggered whenever ANY message arrives on the powerButtonPort
                     ('PowerButton', 'Shutdown'),
                     ('IgnitionOff', 'Shutdown'),
                     # This transition is triggered whenever clockTmr expires, transition to self, 
                     # executes the 'Do' methode
                     ('clockTmr_Expired', 'NormalOp')], 
                'Shutdown':
                    [('shutdownTmr_Expired', 'Standby')],
                'ANY':
                    [('PowerRemoved', 'Off')]
            }
            
            super().__init__( dictTransitions=transitions )
                
        
        # Off actions    
        def State_Off_Entry(self):
            print("State_Off_Entry")
            self.moddyPart().bootTmr.stop()
            self.moddyPart().shutdownTmr.stop()
            self.moddyPart().clockTmr.stop()
        # Booting actions
        def State_Booting_Entry(self):
            print("Booting_Entry")
            self.moddyPart().bootTmr.start(5)
    
        # Shutdown actions
        def State_Shutdown_Entry(self):
            self.moddyPart().shutdownTmr.start(2)
        
        # Cursor Blink in NormalOp state
        def State_NormalOp_Entry(self):
            self._clockTime = 100
            
        def State_NormalOp_Do(self):
            self.moddyPart().clockTmr.start(5)                
            self.moddyPart().visualPort.send('time %d' % self._clockTime, 0.1 )
            self._clockTime += 5
            
        # Message handlers
        def State_ANY_powerPort_Msg(self,msg):
            if msg == 'on':
                self.event('PowerApplied')
            elif msg == 'off':
                self.event('PowerRemoved')
                            
        def State_ANY_ignitionPort_Msg(self, msg):
            if msg == 'on':
                self.event('IgnitionOn')
            elif msg == 'off':
                self.event('IgnitionOff')

        def State_ANY_buttonPort_Msg(self, msg):            
            self.event(msg) # Message are directly the event names
        
        # Nested state machine CarInfo System Applications
        class ApplicationsFsm(Fsm):
        
            def __init__(self, parentFsm):
                
                transitions = { 
                    '':
                        [('INITIAL', 'Radio')],
                    'Radio': 
                        [('NaviButton', 'Navi')],
                    'Navi':
                        [('RadioButton', 'Radio')]
                }
                
                super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                
            def State_Radio_Entry(self):
                self.moddyPart().addAnnotation('Radio activated')
        
            def State_Navi_Entry(self):
                self.moddyPart().addAnnotation('Navi activated')
                
        class VolumeFsm(Fsm):
        
            def __init__(self, parentFsm):
                self._volume = 50
                
                transitions = { 
                    '':
                        [('INITIAL', 'On')],
                    'On': 
                        [('MuteButton', 'Mute'),
                         ('VolKnobRight', 'IncVol'),
                         ('VolKnobLeft', 'DecVol')],
                    'IncVol':
                        [('VolChangeDone', 'On')],
                    'DecVol':
                        [('VolChangeDone', 'On')],
                    'Mute':
                        [('MuteButton', 'On'),
                         ('VolKnobRight', 'On')]
                }
                
                super().__init__( dictTransitions=transitions, parentFsm=parentFsm )
                
            def State_On_Do(self):
                self.moddyPart().audioPort.send('volume=%d' % self._volume, 0.1)
                
            def State_Mute_Do(self):
                self.moddyPart().audioPort.send('volume=%d' % 0, 0.1)

            def State_IncVol_Entry(self):
                self._volume += 1
                self.topFsm().event('VolChangeDone')

            def State_DecVol_Entry(self):
                self._volume -= 1
                self.topFsm().event('VolChangeDone')
 
class Stim(vSimpleProg):   
    def __init__(self, sim):
        super().__init__(sim=sim, objName="Stim", parentObj=None)
        self.createPorts('out', ['powerPort', 'ignitionPort', 'buttonPort']) 
        self.createPorts('SamplingIn', ['audioPort', 'visualPort']) 
        self.ignitionPort.setColor('red')
        self.buttonPort.setColor('blue')
        
    def runVThread(self):
        while True:
            self.powerPort.send('on',1)
            self.wait(2)
            self.buttonPort.send('PowerButton',1)
            self.wait(8)
            self.buttonPort.send( 'NaviButton', 0.5)
            self.wait(2)
            self.buttonPort.send( 'VolKnobRight', 0.5)
            self.buttonPort.send( 'VolKnobRight', 0.5)
            self.wait(1)
            self.buttonPort.send( 'VolKnobLeft', 0.5)
            self.wait(1)
            self.buttonPort.send( 'MuteButton', 0.5)
            self.wait(1)
            self.buttonPort.send( 'VolKnobRight', 0.5)
            self.wait(5)
            self.ignitionPort.send('off',1)
            self.wait(2)
            self.powerPort.send('off',1)
            self.wait(1000)
    
         
        
if __name__ == '__main__':         
    simu = sim()
    cis = CarInfoSystem(simu, "CarInfoSys")
    stim = Stim(simu)
    
    # bind ports
    stim.powerPort.bind(cis.powerPort)
    stim.ignitionPort.bind(cis.ignitionPort)
    stim.buttonPort.bind(cis.buttonPort)
    cis.visualPort.bind(stim.visualPort)
    cis.audioPort.bind(stim.audioPort)
        
    moddyGenerateFsmGraph( fsm=cis.fsm, fileName='output/3_carinfo_fsm.svg', keepGvFile=True)  
    
    
    simu.run(100)
    
    moddyGenerateSequenceDiagram( sim=simu, 
                              fileName="output/3_carinfo.html", 
                              fmt="iaViewerRef", 
                              showPartsList=[stim, cis], 
                              timePerDiv = 0.3, 
                              pixPerDiv = 30,
                              title = "Car Info FSM Demo") 
    
