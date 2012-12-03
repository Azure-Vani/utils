# not defermined => -1
# AC => 0
# TLE => 1
# RE => 2
# WA => 3
# CE =>4
# P => 6
# source not found => 5

require 'fileutils'
require 'find'

t1 = "hadou"
t2 = "dandelion"
t3 = "dream"

$test_case = {t1 => 10, t2 => 20, t3 => 20}
$time_limit = {t1 => 5, t2 => 2.5, t3 => 2}
$tmp_file = '_tmp'
$spj_f = {t1 => 1, t2 => 0, t3 => 0}
$spj = {t1 => "../hadou/spj"}

$status_map = {0 => 'A', 1 => 'T', 2 => 'B', 3 => 'W', 4 => '-', 5 => '?', 6 => 'P'}
$compile_cmd = {"cpp"=>"timeout 5 g++ -o %s %s.cpp &>/dev/null", "c"=>"timeout 5 gcc -o %s %s.c &>/dev/null", "pas"=>"timeout 5 fpc %s.pas  &>/dev/null #%s"}
$problem_list = [t1, t2, t3]

def compile(filename, suffix)
	ret = true
	`#{$compile_cmd[suffix]%[filename, filename]}`
	if $?.to_i != 0
		ret = false
	end
	return ret
end

class Problem
	def initialize(name, time_limit, test_cases = 10)
		@name = name
		@time_limit = time_limit
		@test_cases = test_cases
	end
	def verify(input, output, std_output)
		case_sc = 100 / @test_cases
		if $spj_f[@name] == 0
			`diff -b --ignore-blank-lines #{output} #{std_output} > /dev/null 2>&1`
			if $? == 0
				return [0, case_sc]
			else
				return [3, 0]
			end
		else
			sc = `#{$spj[@name]} #{case_sc} #{input} #{std_output} #{output}`.to_i
			if sc == 0
				return [3, 0]
			elsif sc == case_sc
				return [0, case_sc]
			else
				return [6, sc]
			end
		end
	end
	def each_case
		1.upto(@test_cases) do |i|
			FileUtils::cp("../#@name/#@name#{i}.in", "#$tmp_file/#@name.in")
			print "		Test Case #{i}: "
			yield("#$tmp_file/#@name.in", "#$tmp_file/#@name.out", "../#@name/#@name#{i}.out")
			FileUtils::rm("#$tmp_file/#@name.in")
		end
	end

	def exec
		Dir.chdir($tmp_file)
		ret = `{ time { timeout #@time_limit ./#@name >/dev/null; }; } 2>&1`
		Dir.chdir("..")
		tim = /real\s*([^m]*)m([^s]*)s/.match(ret)
		used_time = (tim[1].to_f * 60 * 1000 + tim[2].to_f *  1000).to_i
		return [used_time, 1] if /exit (\d*)/.match("#$?")[1].to_i == 124
		return [used_time, 2] if $? != 0
		return [used_time, -1]
	end

	def ini
		ret = [5] * @test_cases
	end

	def ce
		ret = [4] * @test_cases
	end
end

$NAME_LENGTH = 10

$problem = {}

$problem_list.each do |now|
	$problem[now] = Problem.new(now, $time_limit[now], $test_case[now])
end

def expand(st, l)
	(l - st.length).times {st += ' '}
	return st
end

class Contestant
	attr_reader :name, :score, :time
	attr_writer :name, :score, :time
	def initialize(name)
		@name = name
		@score = 0
		@time = 0
		@status = {}
	end

	def each_problem
		$problem_list.each do |now_problem|
			puts "	---#{now_problem}"
			@status[now_problem] = $problem[now_problem].ini
			FileUtils::mkdir($tmp_file)
			['cpp', 'pas', 'c'].each do |suffix|
				source_name = @name + '/' + now_problem + '.' + suffix
				if File.exist?(source_name)
					FileUtils::cp(source_name, $tmp_file)
					compile_flag = compile($tmp_file + '/' + now_problem, suffix)
					if compile_flag == false
						@status[now_problem] = $problem[now_problem].ce
						break
					end
					score, time, status = yield(now_problem)
					@score += score
					@time += time
					@status[now_problem] = status
					break
				end
			end
			FileUtils::rm_rf($tmp_file)
		end
	end

	def to_s
		ret = ""
		ret += expand(@name, $NAME_LENGTH)
		@status.each do |x|
			x[1].each do |t|
				ret += $status_map[t]
			end
			ret += ' '
		end
		ret += "   #@score"
	end
end

def gen_contestant
	ret = []
	Dir.foreach('.') do |item|
		if item != "." and item != ".."
			ret << item if File.directory?(item)
		end
	end
	return ret
end

def evaluate
	#get contestant list
	contestant_list_str = gen_contestant
	contestant = []
	contestant_list_str.each do |now|
		tmp = Contestant.new(now)
		contestant << tmp.dup
	end
	#evaluate
	contestant.each do |now|
		puts "Evaluting.... #{now.name}"
		now.each_problem do |problem_now|
			item = $problem[problem_now]
			status = []
			score = 0
			time = 0
			item.each_case do |input, output, std_output|
				t_time, t_flag = item.exec
				if t_flag == -1
					t_flag, sc = item.verify(input, output, std_output)
					score += sc
				end
				status << t_flag
				time += t_time
				puts "Done...      Time: #{t_time}ms"
			end
			puts "	time used #{time}ms"
			[score, time, status].dup
		end
	end
	#Sort contestant list
	contestant.sort! {|a, b| a.score != b.score ? b.score <=> a.score : a.time <=> b.time}
	#output
	oup = File.open("result", "w")
	contestant.each {|x| oup.puts x}
	oup.close
end

begin
	evaluate
ensure
	if File.directory?"./_tmp"
		FileUtils::rm_rf("./_tmp")
	end
end

