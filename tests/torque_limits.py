# -*- coding: utf-8 -*-
# Copyright (C) 2013 Quang-Cuong Pham <cuong.pham@normalesup.org>
#
# This file is part of the Time-Optimal Path Parameterization (TOPP) library.
# TOPP is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

print("\n************************************\nNB: This test file requires OpenRAVE\n************************************\n")

import time
from pylab import *
from numpy import *
from openravepy import *
from TOPP import TOPPbindings
from TOPP import TOPPpy
from TOPP import TOPPopenravepy
from TOPP import Trajectory
from TOPP import Utilities

try:
    input = raw_input
except NameError:
    pass


# Robot (OpenRAVE)
env = Environment()
env.Load("robots/barrettwam.robot.xml")
env.SetViewer('qtcoin')
env.GetViewer().SetCamera(array([[ 0.92038107,  0.00847738, -0.39093071,  0.69997793],
       [ 0.39101295, -0.02698477,  0.91998951, -1.71402919],
       [-0.00275007, -0.9995999 , -0.02815103,  0.40470174],
       [ 0.        ,  0.        ,  0.        ,  1.        ]]))
robot=env.GetRobots()[0]
grav=[0,0,-9.8]
ndof=robot.GetDOF()
dof_lim=robot.GetDOFLimits()
vel_lim=robot.GetDOFVelocityLimits()
robot.SetDOFLimits(-10*ones(ndof),10*ones(ndof)) # Overrides robot joint limits for TOPP computations
robot.SetDOFVelocityLimits(100*vel_lim) # Override robot velocity limits for TOPP computations

# Trajectory
q0 = zeros(ndof)
q1 = zeros(ndof)
qd0 = ones(ndof)
qd1 = -ones(ndof)
q0[0:7] = [-2,0.5,1,3,-3,-2,-2]
q1[0:7] = [2,-0.5,-1,-1,1,1,1]
T = 1.5
trajectorystring = "%f\n%d"%(T,ndof)
for i in range(ndof):
    a,b,c,d = Utilities.Interpolate3rdDegree(q0[i],q1[i],qd0[i],qd1[i],T)
    trajectorystring += "\n%f %f %f %f"%(d,c,b,a)
traj0 = Trajectory.PiecewisePolynomialTrajectory.FromString(trajectorystring)

# Constraints
vmax = zeros(ndof)
taumin = zeros(ndof)
taumax = zeros(ndof)
vmax[0:7] = vel_lim[0:7]  # Velocity limits
taumin[0:7] = -robot.GetDOFMaxTorque()[0:7] # Torque limits
taumax[0:7] = robot.GetDOFMaxTorque()[0:7] # Torque limits

# Set up the TOPP problem
discrtimestep = 0.005
uselegacy = False
t0 = time.time()
if uselegacy: #Using the legacy TorqueLimits (faster but not fully supported)
    constraintstring = str(discrtimestep)
    constraintstring += "\n" + " ".join([str(v) for v in vmax])
    constraintstring += "\n" + " ".join([str(t) for t in taumin]) 
    constraintstring += "\n" + " ".join([str(t) for t in taumax]) 
    x = TOPPbindings.TOPPInstance(robot,"TorqueLimitsRave", constraintstring, trajectorystring)
else: #Using the general QuadraticConstraints (fully supported)
    constraintstring = str(discrtimestep)
    constraintstring += "\n" + " ".join([str(v) for v in vmax])
    constraintstring += TOPPopenravepy.ComputeTorquesConstraints(robot,traj0,taumin,taumax,discrtimestep)
    x = TOPPbindings.TOPPInstance(None,"QuadraticConstraints",constraintstring,trajectorystring);

# Run TOPP
t1 = time.time()
ret = x.RunComputeProfiles(0,0)
if(ret == 1):
    x.ReparameterizeTrajectory()
t2 = time.time()

print("Using legacy:", uselegacy)
print("Discretization step:", discrtimestep)
print("Setup TOPP:", t1-t0)
print("Run TOPP:", t2-t1)
print("Total:", t2-t0)

# Display results
ion()
x.WriteProfilesList()
x.WriteSwitchPointsList()
profileslist = TOPPpy.ProfilesFromString(x.resprofilesliststring)
switchpointslist = TOPPpy.SwitchPointsFromString(x.switchpointsliststring)

if(ret == 1):
    x.WriteResultTrajectory()
    traj1 = Trajectory.PiecewisePolynomialTrajectory.FromString(x.restrajectorystring)

    # Execute trajectory
    TOPPopenravepy.Execute(robot,traj1)

    dtplot = 0.01
    TOPPpy.PlotProfiles(profileslist,switchpointslist,4)
    TOPPpy.PlotKinematics(traj0,traj1,dtplot,vmax)
    TOPPopenravepy.PlotTorques(robot,traj0,traj1,dtplot,taumin,taumax,3)


input()
