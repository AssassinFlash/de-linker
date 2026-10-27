# Energy workspace copy draft

English source draft before adversarial review. These are tool controls, explanations and frozen-result output, not homepage marketing. Existing source shown in overview/editor is included for integration context; preserve already-approved German and mark new German separately. Source root: apps/planner.

1. **src/components/energy/EnergyError.tsx:9**

   The scenario needs gross-load, available-PV and separate AC auxiliary interval profiles.

2. **src/components/energy/EnergyError.tsx:14**

   The storage parameters need a source or assumption note.

3. **src/components/energy/EnergyError.tsx:19**

   Storage values need attention. Efficiencies must be greater than 0% and no more than 100%; other storage values must be zero or greater.

4. **src/components/energy/EnergyError.tsx:24**

   The three starting-energy amounts and their basis are required. An empty starting inventory can be selected explicitly.

5. **src/components/energy/EnergyError.tsx:29**

   Initial stored energy exceeds the usable energy window.

6. **src/components/energy/EnergyError.tsx:34**

   The final-inventory requirement needs a choice and, when applicable, a minimum value.

7. **src/components/energy/EnergyError.tsx:39**

   An operating period is incomplete. An outage also needs a critical-load profile.

8. **src/components/energy/EnergyError.tsx:44**

   Period timestamps need a date, time and Z or a numeric UTC offset.

9. **src/components/energy/EnergyError.tsx:49**

   Reserved energy exceeds the usable energy window.

10. **src/components/energy/EnergyError.tsx:54**

   A specified import or export cap needs its value in kW. Zero is allowed.

11. **src/components/energy/EnergyError.tsx:59**

   Grid charging cannot be enabled during an outage.

12. **src/components/energy/EnergyError.tsx:64**

   The storage settings have changed and need to be prepared again.

13. **src/components/energy/EnergyError.tsx:69**

   The inputs changed while this request was being prepared. The current draft is kept; the saved request can be retried explicitly.

14. **src/components/energy/EnergyError.tsx:74**

   The required profiles have no shared time range.

15. **src/components/energy/EnergyError.tsx:79**

   New calculations are temporarily unavailable while the service is being updated. This request is kept for retry.

16. **src/components/energy/EnergyError.tsx:84**

   The saved revision or request has changed. The open inputs and original request are kept for review.

17. **src/components/energy/EnergyError.tsx:90**

   The scenario could not be accepted. Profile coverage, operating periods and storage settings need review.

18. **src/components/energy/EnergyError.tsx:100**

   This calculation reply could not be verified. Saved calculations and the original request remain available.

19. **src/components/energy/EnergyError.tsx:105**

   The request could not be confirmed. The original request and open inputs are kept.

20. **src/components/ProjectEditor.tsx:465**

   Energy calculation

21. **src/components/energy/EnergyWorkspace.tsx:399**

   A saved scenario calculates energy flows over your interval data. The result retains its input revision, sources and model.

22. **src/components/energy/EnergyWorkspace.tsx:409**

   Calculation workspace view

23. **src/components/energy/EnergyWorkspace.tsx:416**

   Scenario settings

24. **src/components/energy/EnergyWorkspace.tsx:423**

   Saved calculations

25. **src/components/energy/EnergyWorkspace.tsx:430**

   Calculation-request recovery could not be stored or checked. New requests need durable recovery before they can be sent.

26. **src/components/energy/EnergyWorkspace.tsx:440**

   Check request recovery

27. **src/components/energy/EnergyWorkspace.tsx:449**

   Stored requests

28. **src/components/energy/EnergyWorkspace.tsx:451**

   Retry keeps the original request and key. Restoring storage parameters changes that part of the open draft; calculation requests keep their original saved revision.

29. **src/components/energy/EnergyWorkspace.tsx:463**

   Stored storage parameters

30. **src/components/energy/EnergyWorkspace.tsx:464**

   Calculation request · revision %d

31. **src/components/energy/EnergyWorkspace.tsx:479**

   Restore and retry storage settings

32. **src/components/energy/EnergyWorkspace.tsx:480**

   Retry original calculation request

33. **src/components/energy/EnergyWorkspace.tsx:486**

   Dismiss confirmed request

34. **src/components/energy/EnergyWorkspace.tsx:496**

   This scenario-settings format cannot be edited here. Its saved input and calculation history remain available.

35. **src/components/energy/EnergyWorkspace.tsx:505**

   Interval sources

36. **src/components/energy/EnergyWorkspace.tsx:513**

   Selected in this draft

37. **src/components/energy/EnergyWorkspace.tsx:514**

   Required

38. **src/components/energy/EnergyWorkspace.tsx:526**

   Review energy inputs

39. **src/components/energy/EnergyWorkspace.tsx:543**

   Storage

40. **src/components/energy/EnergyWorkspace.tsx:545**

   Starting state

41. **src/components/energy/EnergyWorkspace.tsx:546**

   Operation

42. **src/components/energy/EnergyWorkspace.tsx:566**

   Scenario prepared in this draft

43. **src/components/energy/EnergyWorkspace.tsx:567**

   Scenario settings need preparation

44. **src/components/energy/EnergyWorkspace.tsx:571**

   Save project records these inputs before a new calculation can start.

45. **src/components/energy/EnergyWorkspace.tsx:575**

   A new calculation uses saved input revision %d.

46. **src/components/energy/EnergyWorkspace.tsx:598**

   Confirming request…

47. **src/components/energy/EnergyWorkspace.tsx:599**

   Prepare scenario settings

48. **src/components/energy/EnergyWorkspace.tsx:607**

   Calculate saved scenario

49. **src/components/energy/EnergyWorkspace.tsx:617**

   Saved calculation history could not be refreshed.

50. **src/components/energy/EnergyWorkspace.tsx:627**

   Refresh calculation history

51. **src/components/energy/EnergyWorkspace.tsx:633**

   Reading saved calculations…

52. **src/components/energy/EnergyWorkspace.tsx:638**

   Calculation history

53. **src/components/energy/EnergyWorkspace.tsx:641**

   No saved calculation is available on this page.

54. **src/components/energy/EnergyWorkspace.tsx:655**

   Revision %d

55. **src/components/energy/EnergyWorkspace.tsx:673**

   Latest calculations

56. **src/components/energy/EnergyWorkspace.tsx:682**

   Earlier calculations

57. **src/components/energy/EnergyWorkspace.tsx:692**

   The selected calculation could not be refreshed. Any visible state is the last confirmed response.

58. **src/components/energy/EnergyWorkspace.tsx:702**

   Refresh calculation status

59. **src/components/energy/EnergyWorkspace.tsx:708**

   Reading the saved calculation…

60. **src/components/energy/EnergyWorkspace.tsx:735**

   Confirming cancellation…

61. **src/components/energy/EnergyWorkspace.tsx:736**

   Cancel calculation

62. **src/components/energy/EnergyWorkspace.tsx:741**

   Cancellation could not be confirmed. The calculation may still be running; its server status can be refreshed.

63. **src/components/energy/OperatingPeriodForm.tsx:43**

   Operating period %d

64. **src/components/energy/OperatingPeriodForm.tsx:47**

   Start with UTC or offset

65. **src/components/energy/OperatingPeriodForm.tsx:56**

   End with UTC or offset

66. **src/components/energy/RunBasis.tsx:250**

   Grid condition

67. **src/components/energy/ScenarioForm.tsx:295**

   Choose an option

68. **src/components/energy/RunBasis.tsx:262**

   Grid connected

69. **src/components/energy/RunBasis.tsx:261**

   Grid outage

70. **src/components/energy/OperatingPeriodForm.tsx:85**

   Reserved stored energy

71. **src/components/energy/OperatingPeriodForm.tsx:93**

   PV available in this period

72. **src/components/energy/OperatingPeriodForm.tsx:106**

   Available

73. **src/components/energy/OperatingPeriodForm.tsx:107**

   Unavailable

74. **src/components/energy/OperatingPeriodForm.tsx:112**

   Grid charging allowed

75. **src/components/energy/OperatingPeriodForm.tsx:129**

   Allowed

76. **src/components/energy/OperatingPeriodForm.tsx:130**

   Not allowed

77. **src/components/energy/OperatingPeriodForm.tsx:137**

   Grid import limit

78. **src/components/energy/OperatingPeriodForm.tsx:184**

   No cap in this scenario

79. **src/components/energy/OperatingPeriodForm.tsx:187**

   Specified cap

80. **src/components/energy/OperatingPeriodForm.tsx:161**

   Import cap

81. **src/components/energy/OperatingPeriodForm.tsx:170**

   Grid export limit

82. **src/components/energy/OperatingPeriodForm.tsx:194**

   Export cap

83. **src/components/energy/OperatingPeriodForm.tsx:207**

   During an outage, grid import, export and charging are zero. A critical-load profile and an explicit PV availability choice are required.

84. **src/components/energy/OperatingPeriodForm.tsx:215**

   Remove operating period

85. **src/components/energy/ScenarioForm.tsx:12**

   Usable stored energy

86. **src/components/energy/ScenarioForm.tsx:14**

   AC charging power

87. **src/components/energy/ScenarioForm.tsx:16**

   AC discharging power

88. **src/components/energy/ScenarioForm.tsx:18**

   Charging efficiency

89. **src/components/energy/ScenarioForm.tsx:20**

   Discharging efficiency

90. **src/components/energy/ScenarioForm.tsx:22**

   Internal auxiliary power

91. **src/components/energy/ScenarioForm.tsx:24**

   Standing-loss coefficient

92. **src/components/energy/RunBasis.tsx:157**

   Sources, period and storage model

93. **src/components/energy/RunBasis.tsx:163**

   Reading the pinned input sources…

94. **src/components/energy/RunBasis.tsx:169**

   The pinned source records could not be read. The saved result has been kept without substituting newer sources.

95. **src/components/energy/RunBasis.tsx:179**

   Retry source records

96. **src/components/energy/RunBasis.tsx:194**

   Original content SHA-256

97. **src/components/energy/RunBasis.tsx:201**

   Source metadata SHA-256

98. **src/components/energy/RunBasis.tsx:236**

   The model uses a fixed internal energy window and separate AC conversion efficiencies. Battery export, temperature effects, ageing and switching behaviour are outside this energy calculation.

99. **src/components/energy/RunBasis.tsx:244**

   Calculated operating periods (UTC)

100. **src/components/energy/RunBasis.tsx:248**

   Start

101. **src/components/energy/RunBasis.tsx:249**

   End

102. **src/components/energy/RunBasis.tsx:251**

   Source resolution

103. **src/components/energy/RunBasis.tsx:275**

   Reconstructed interval means

104. **src/components/energy/RunBasis.tsx:292**

   Time alignment preserves interval energy under a constant-mean assumption. A finer display or operating boundary does not create new measured peaks.

105. **src/components/energy/RunResult.tsx:9**

   Queued

106. **src/components/energy/RunResult.tsx:11**

   Calculating

107. **src/components/energy/RunResult.tsx:13**

   Waiting to retry

108. **src/components/energy/RunResult.tsx:15**

   Calculation complete

109. **src/components/energy/RunResult.tsx:17**

   Calculation failed

110. **src/components/energy/RunResult.tsx:19**

   Calculation cancelled

111. **src/components/energy/RunResult.tsx:25**

   A pinned model or source is unavailable. This calculation has been kept with its original inputs.

112. **src/components/energy/RunResult.tsx:30**

   The saved scenario could not be calculated. Source coverage, operating periods or storage settings need attention.

113. **src/components/energy/RunResult.tsx:35**

   The calculation exceeded the service's current processing limit. Its original inputs remain saved.

114. **src/components/energy/RunResult.tsx:40**

   The numerical checks could not establish a usable result. The saved inputs remain available.

115. **src/components/energy/RunResult.tsx:45**

   The calculation stopped before a result was published. Its original inputs remain saved.

116. **src/components/energy/RunResult.tsx:86**

   Saved calculation

117. **src/components/energy/RunResult.tsx:91**

   Input revision %d

118. **src/components/energy/RunResult.tsx:96**

   This calculation uses an earlier input snapshot. Open or newer project changes are excluded from its result.

119. **src/components/energy/RunResult.tsx:104**

   The saved task runs on the server. Leaving this workspace keeps it running; cancellation uses the separate cancel action.

120. **src/components/energy/RunResult.tsx:113**

   The server has confirmed cancellation. Any earlier saved results remain available.

121. **src/components/energy/RunResult.tsx:123**

   The calculation checks need attention. The detailed checks identify unmet requirements or inconsistencies.

122. **src/components/energy/RunResult.tsx:131**

   Solar supplied to load

123. **src/components/energy/RunResult.tsx:137**

   Grid import

124. **src/components/energy/RunResult.tsx:143**

   Solar share of gross demand

125. **src/components/energy/RunResult.tsx:147**

   PV energy used on site

126. **src/components/energy/RunResult.tsx:152**

   Figures cover the simulated periods. Solar supply includes PV-origin battery energy; grid-origin and unknown-origin inventory remain separate.

127. **src/components/energy/RunResult.tsx:159**

   This calculation includes critical-load periods. A whole-site gross-demand percentage is therefore undefined.

128. **src/components/energy/RunResult.tsx:167**

   The PV-use percentage is undefined when generated PV energy is zero.

129. **src/components/energy/RunResult.tsx:175**

   Equipment suitability: not assessed by this calculation.

130. **src/components/energy/RunResult.tsx:181**

   Country requirements: not assessed by this calculation.

131. **src/components/energy/RunResult.tsx:189**

   Energy totals and definitions

132. **src/components/energy/RunResult.tsx:193**

   Simulated load demand

133. **src/components/energy/RunResult.tsx:197**

   Generated AC PV energy

134. **src/components/energy/RunResult.tsx:201**

   Unserved simulated load

135. **src/components/energy/RunResult.tsx:205**

   Calculated intervals

136. **src/components/energy/RunResult.tsx:210**

   Solar share of gross demand divides PV energy delivered to gross site load by gross site demand. It is undefined for a mixed or critical-only load scope, or zero gross demand.

137. **src/components/energy/RunResult.tsx:216**

   PV energy used on site divides PV supplied to load, AC auxiliaries and battery charging by generated PV after curtailment. Battery conversion losses remain in the energy balance.

138. **src/components/energy/RunResult.tsx:223**

   Calculation checks

139. **src/components/energy/RunResult.tsx:225**

   These checks cover the declared energy model and scenario. Their numerical allowances address floating-point arithmetic; they are not installation safety margins.

140. **src/components/energy/RunResult.tsx:233**

   Frozen verification checks

141. **src/components/energy/RunResult.tsx:237**

   Check

142. **src/components/energy/RunResult.tsx:238**

   Outcome

143. **src/components/energy/RunResult.tsx:239**

   Largest violation

144. **src/components/energy/RunResult.tsx:240**

   Numerical allowance

145. **src/components/energy/RunResult.tsx:255**

   Met

146. **src/components/energy/RunResult.tsx:256**

   Needs attention

147. **src/components/energy/RunResult.tsx:274**

   Pinned calculation records

148. **src/components/energy/RunResult.tsx:278**

   Input SHA-256

149. **src/components/energy/RunResult.tsx:284**

   Manifest SHA-256

150. **src/components/energy/RunResult.tsx:290**

   Result SHA-256

151. **src/components/energy/RunResult.tsx:296**

   Runtime SHA-256

152. **src/components/energy/RunResult.tsx:302**

   Energy trace SHA-256

153. **src/components/energy/ScenarioForm.tsx:60**

   Storage parameters

154. **src/components/energy/ScenarioForm.tsx:62**

   These declared parameters describe a storage scenario at one AC connection. Product suitability is assessed separately.

155. **src/components/energy/ScenarioForm.tsx:112**

   Source for storage parameters

156. **src/components/energy/ScenarioForm.tsx:126**

   Storage model and units

157. **src/components/energy/ScenarioForm.tsx:128**

   Usable stored energy is the model's internal energy window. Charging and discharging power are measured at the AC connection. The two efficiencies describe their separate conversion directions.

158. **src/components/energy/ScenarioForm.tsx:134**

   Internal auxiliary power is drawn from stored energy. Separate AC auxiliary demand comes from its interval profile. Standing loss uses E × (1 − exp(−r × hours)), with r in 1/h. Zero losses are explicit scenario assumptions.

159. **src/components/energy/ScenarioForm.tsx:140**

   This model uses fixed capacity, power and efficiency. Temperature effects, ageing, shared DC ports, phase limits and switching behaviour require their own assessment.

160. **src/components/energy/ScenarioForm.tsx:148**

   Initial stored energy

161. **src/components/energy/ScenarioForm.tsx:150**

   Stored energy keeps its origin throughout the calculation. Energy from the grid or an unknown source is excluded from the solar-supplied total.

162. **src/components/energy/ScenarioForm.tsx:163**

   From PV

163. **src/components/energy/ScenarioForm.tsx:165**

   From the grid

164. **src/components/energy/ScenarioForm.tsx:166**

   Origin unknown

165. **src/components/energy/ScenarioForm.tsx:192**

   Empty stored-energy inventory selected for the start of this scenario.

166. **src/components/energy/ScenarioForm.tsx:200**

   Start with an empty battery

167. **src/components/energy/ScenarioForm.tsx:203**

   Basis for the initial state

168. **src/components/energy/ScenarioForm.tsx:220**

   Operating periods

169. **src/components/energy/ScenarioForm.tsx:222**

   Periods must join without gaps or overlaps and stay within the source data. Timestamps include Z for UTC or an explicit offset, such as +01:00.

170. **src/components/energy/ScenarioForm.tsx:234**

   Checking profile coverage…

171. **src/components/energy/ScenarioForm.tsx:235**

   Use the shared profile range

172. **src/components/energy/ScenarioForm.tsx:281**

   Add operating period

173. **src/components/energy/ScenarioForm.tsx:284**

   End-of-period requirement

174. **src/components/energy/ScenarioForm.tsx:297**

   No minimum final inventory

175. **src/components/energy/ScenarioForm.tsx:300**

   Minimum final inventory

176. **src/components/energy/ScenarioForm.tsx:307**

   Minimum stored energy at the end

177. **src/components/energy/ScenarioForm.tsx:318**

   How storage is operated

178. **src/components/energy/ScenarioForm.tsx:320**

   PV supplies the simulated load and AC auxiliary demand before charging storage. Storage covers remaining demand above its reserve. Grid charging, when allowed, restores the reserve. Surplus PV is exported within the cap and then curtailed.

179. **src/components/energy/ScenarioForm.tsx:326**

   Stored energy continues across every period. The model excludes battery export and does not reset the battery at midnight or at the start of an outage.

180. **src/components/ProjectEditor.tsx:421**

   Project overview

181. **src/components/ProjectOverview.tsx:40**

   Your project at a glance

182. **src/components/ProjectOverview.tsx:43**

   Site information, roof layouts and energy inputs share this project. Each workspace can be completed as the design develops.

183. **src/components/ProjectOverview.tsx:51**

   Country

184. **src/components/ProjectOverview.tsx:58**

   Project location

185. **src/components/ProjectOverview.tsx:61**

   Annual consumption

186. **src/components/ProjectOverview.tsx:70**

   Electricity bills

187. **src/components/ProjectOverview.tsx:72**

   Project estimate

188. **src/components/ProjectOverview.tsx:73**

   Basis not specified

189. **src/components/ProjectOverview.tsx:77**

   Included modules

190. **src/components/ProjectOverview.tsx:79**

   Across the current roof layouts

191. **src/components/ProjectOverview.tsx:82**

   Declared DC nameplate power

192. **src/components/ProjectOverview.tsx:94**

   Module count and declared specifications

193. **src/components/ProjectOverview.tsx:105**

   Current layout

194. **src/components/ProjectOverview.tsx:143**

   Open roof workspace

195. **src/components/ProjectOverview.tsx:130**

   A place for the roof and its layout

196. **src/components/ProjectOverview.tsx:133**

   Roof design is optional. A measured roof can be added here while the project information and energy inputs remain available in their workspaces.

197. **src/components/ProjectOverview.tsx:151**

   Project workspaces

198. **src/components/ProjectOverview.tsx:153**

   Continue your project

199. **src/components/ProjectEditor.tsx:432**

   Site and project

200. **src/components/ProjectOverview.tsx:159**

   Location, system scope and site conditions

201. **src/components/ProjectEditor.tsx:443**

   Roof design

202. **src/components/ProjectOverview.tsx:173**

   Roof faces, obstacles and module layout

203. **src/components/ProjectEditor.tsx:454**

   Energy inputs

204. **src/components/ProjectOverview.tsx:183**

   Annual consumption and interval data

205. **src/components/ProjectOverview.tsx:193**

   Scenario settings and saved calculations

206. **src/components/ProjectOverview.tsx:199**

   The overview describes the current inputs. Energy yield, equipment suitability and engineering release require their respective calculations and evidence.

207. **src/components/ProjectEditor.tsx:256**

   Opening project…

208. **src/components/ProjectEditor.tsx:278**

   This project contains an input format that this workspace cannot edit.

209. **src/components/ProjectEditor.tsx:296**

   Projects

210. **src/components/ProjectEditor.tsx:411**

   Project sections

211. **src/components/ProjectEditor.tsx:326**

   Saving…

212. **src/components/ProjectEditor.tsx:328**

   Save not confirmed

213. **src/components/ProjectEditor.tsx:330**

   Input needs attention

214. **src/components/ProjectEditor.tsx:332**

   Roof editing in progress

215. **src/components/ProjectEditor.tsx:334**

   Unsaved changes

216. **src/components/ProjectEditor.tsx:335**

   Saved · revision %d

217. **src/components/ProjectEditor.tsx:343**

   Undo

218. **src/components/ProjectEditor.tsx:352**

   Redo

219. **src/components/ProjectEditor.tsx:372**

   Retry save

220. **src/components/ProjectEditor.tsx:373**

   Save project

221. **src/components/ProjectEditor.tsx:383**

   Correct the highlighted input before leaving this project.

222. **src/components/ProjectEditor.tsx:388**

   Finish or cancel roof editing before leaving this workspace.

223. **src/components/ProjectEditor.tsx:392**

   Save the project before leaving. Browser recovery could not be stored.

224. **src/components/ProjectEditor.tsx:406**

   Solution Configurator

225. **src/components/ProjectEditor.tsx:481**

   Current project

226. **src/components/ProjectEditor.tsx:471**

   Project information is kept with its source and revision.

227. **src/components/ProjectEditor.tsx:485**

   Site data and roof layouts are saved in the same project.

228. **src/components/ProjectEditor.tsx:494**

   Unconfirmed project creations and CSV imports from earlier sessions could not be checked. Any recovery data already stored in this browser remains unchanged.

229. **src/components/ProjectEditor.tsx:500**

   Check session

230. **src/components/ProjectEditor.tsx:507**

   Several local drafts are available for this project. Select one to compare with the saved revision.

231. **src/components/ProjectEditor.tsx:519**

   Local draft · revision %d

232. **src/components/ProjectEditor.tsx:532**

   Unsaved work from this browser has been restored.

233. **src/components/ProjectEditor.tsx:540**

   Browser recovery is unavailable. Changes remain open here until the server confirms a save.

234. **src/components/ProjectEditor.tsx:548**

   The save could not be confirmed. Your input is still here.

235. **src/components/ProjectEditor.tsx:557**

   Open changes have been kept alongside the saved revision.

236. **src/components/ProjectEditor.tsx:568**

   Keep open changes

237. **src/components/ProjectEditor.tsx:574**

   Use saved revision

238. **src/components/ProjectEditor.tsx:616**

   Interval data

239. **src/components/ProjectEditor.tsx:619**

   After import, the data's meaning and coverage are shown for review. A profile selection applies to the open draft and is saved with Save project. The annual consumption entry remains separate.

240. **src/components/ProjectEditor.tsx:663**

   Remove draft selection

241. **src/components/ProjectEditor.tsx:666**

   Removing a selection leaves the stored source unchanged. Save the project to record the change.
